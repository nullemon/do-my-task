"""Finishing: handheld camera micro-motion, bloom, tone-map, grain, vignette; ffmpeg pipe encoder."""
import subprocess, math
import numpy as np, cv2
from .core import f32, noise1, lin_to_srgb


def handheld(t, amp=1.0, seed=0):
    """(dx, dy, rot_deg) smooth breathing hand-held motion; a few px at 1080 wide"""
    dx = (noise1(t, seed + 1, 0.35, 3) * 3.2 + noise1(t, seed + 2, 1.7, 2) * 0.7) * amp
    dy = (noise1(t, seed + 3, 0.30, 3) * 3.0 + noise1(t, seed + 4, 1.5, 2) * 0.6) * amp
    rot = noise1(t, seed + 5, 0.25, 2) * 0.16 * amp
    return dx, dy, rot


def camera(img, t, zoom=1.0, cx=None, cy=None, amp=1.0, seed=0):
    """apply zoom (about cx, cy) + handheld motion. A base over-scan of 2 % hides the borders."""
    H, W = img.shape[:2]
    cx = W / 2 if cx is None else cx; cy = H / 2 if cy is None else cy
    dx, dy, rot = handheld(t, amp, seed)
    z = zoom * (1.02 + 0.004 * amp)
    M = cv2.getRotationMatrix2D((cx, cy), rot, z)
    M[0, 2] += dx + (W / 2 - cx) * 0; M[1, 2] += dy
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def bloom(img, amt=1.0):
    H, W = img.shape[:2]
    small = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    acc = np.zeros_like(small)
    for s, wg in ((1.5, 0.30), (5, 0.25), (15, 0.20), (45, 0.16), (110, 0.09)):
        acc += cv2.GaussianBlur(small, (0, 0), s) * wg
    return img + cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR) * amt * 0.35


def tonemap(img, expo=1.0):
    """filmic shoulder with highlight desaturation; returns sRGB 0..1"""
    x = np.maximum(img * expo, 0)
    l = x @ np.array([0.2126, 0.7152, 0.0722], f32)
    k = np.clip((l - 0.8) / 6.0, 0, 0.8)[..., None]
    x = x * (1 - k) + l[..., None] * k
    y = 1 - np.exp(-x * 1.12)
    return lin_to_srgb(y)


_vig = {}
def finish(srgb, t, grain=0.011, vignette=0.22, seed=0):
    H, W = srgb.shape[:2]
    if (H, W) not in _vig:
        yy, xx = np.mgrid[0:H, 0:W].astype(f32)
        r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 * 0.8 + ((yy - H / 2) / (H / 2)) ** 2 * 0.8)
        _vig[(H, W)] = (1 - vignette * np.clip(r - 0.35, 0, 1) ** 1.6)[..., None].astype(f32)
    out = srgb * _vig[(H, W)]
    rng = np.random.default_rng(int(t * 1000) + seed)
    g = rng.standard_normal((H // 2, W // 2)).astype(f32)
    g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)
    lw = np.clip(0.25 + 0.75 * (1 - np.abs(out.mean(2, keepdims=True) - 0.45) * 1.8), 0.2, 1)
    return np.clip(out + g[..., None] * grain * lw, 0, 1)


class Encoder:
    def __init__(self, path, W, H, fps=30, crf=16, preset="slow"):
        self.p = subprocess.Popen(["nice", "-n", "10", "ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                                   "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-threads", "2",
                                   "-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart", path], stdin=subprocess.PIPE)

    def write(self, srgb):
        self.p.stdin.write((np.clip(srgb, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())

    def close(self):
        self.p.stdin.close(); self.p.wait()
