"""Andromeda sprite for "The Night Andromeda Hits Us" -> SCR/m31.npz (the galaxies-visible prep.py M31 recipe, copied
and re-scaled; that file is untouched). NASA/JPL-Caltech GALEX PIA15416 (via GitHub unit511/space-wallpapers 4K, public
domain), registered with an exact 3-point affine (nucleus, M32, M110 -> their real RA/Dec), which fixes scale, rotation
and handedness. Sprite frame: north up, east left (sky seen from below), K px per degree, centre = nucleus.
Also a mip pyramid (x1/2 .. x1/32) so the renderer can draw it small without aliasing.
Usage: /home/user/ttsenv/bin/python prep.py"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import lib.core  # noqa: F401
import numpy as np, cv2
from PIL import Image
from lib.core import f32, srgb_to_lin, lum, fbm2, smooth

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B3-andromeda-collision"
DL = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B3-common/dl"
K = 500.0                                        # sprite px per degree
SZ = 2048                                        # sprite covers ~4.1 deg

def tan_off(ra, dec, ra0, dec0):
    """gnomonic offsets (E, N) in degrees of (ra, dec) about (ra0, dec0)"""
    a, d, a0, d0 = map(math.radians, (ra, dec, ra0, dec0))
    c = math.sin(d0) * math.sin(d) + math.cos(d0) * math.cos(d) * math.cos(a - a0)
    E = math.cos(d) * math.sin(a - a0) / c
    N = (math.cos(d0) * math.sin(d) - math.sin(d0) * math.cos(d) * math.cos(a - a0)) / c
    return math.degrees(E), math.degrees(N)


def load(p):
    return srgb_to_lin(np.asarray(Image.open(p).convert("RGB"), f32) / 255.0)


def blacklevel(img, pct):
    b = np.percentile(img.reshape(-1, 3), pct, axis=0); return np.maximum(img - b, 0)


def vivid(img, sat, con=1.0):
    y = lum(img)[..., None]
    if con != 1.0:
        mu = float(np.percentile(y, 99.0)) * 0.3 + 1e-4; img = img * (np.maximum(y, 1e-6) / mu) ** (con - 1) ; y = lum(img)[..., None]
    return np.maximum(y + (img - y) * sat, 0).astype(f32)


def ell_mask(h, w, cx, cy, a, b, pa_screen, seed, soft=0.5, rough=0.10):
    """soft noisy ellipse; a, b semi-axes in px; pa_screen = angle of the major axis on the sprite (rad, from +x)"""
    yy, xx = np.mgrid[0:h, 0:w].astype(f32)
    dx, dy = xx - cx, yy - cy; c, s = math.cos(pa_screen), math.sin(pa_screen)
    u = (dx * c + dy * s) / a; v = (-dx * s + dy * c) / b
    n = cv2.resize(fbm2((64, 64), seed, 2.4), (w, h), interpolation=cv2.INTER_CUBIC)
    r = np.sqrt(u * u + v * v) * (1 + rough * n)
    return smooth(1.0, soft, r).astype(f32)


def pa_dir(pa_deg):
    """direction of position angle pa (N through E) in sprite coords (x right = west, y down = south)"""
    p = math.radians(pa_deg); return -math.sin(p), -math.cos(p)


M31 = (10.68471, 41.26875); M32 = (10.67425, 40.86517); M110 = (10.09208, 41.68528)


def tan_off(ra, dec, ra0, dec0):
    """gnomonic offsets (E, N) in degrees of (ra, dec) about (ra0, dec0)"""
    a, d, a0, d0 = map(math.radians, (ra, dec, ra0, dec0))
    c = math.sin(d0) * math.sin(d) + math.cos(d0) * math.cos(d) * math.cos(a - a0)
    E = math.cos(d) * math.sin(a - a0) / c
    N = (math.cos(d0) * math.sin(d) - math.sin(d0) * math.cos(d) * math.cos(a - a0)) / c
    return math.degrees(E), math.degrees(N)


def load(p):
    return srgb_to_lin(np.asarray(Image.open(p).convert("RGB"), f32) / 255.0)


def blacklevel(img, pct):
    b = np.percentile(img.reshape(-1, 3), pct, axis=0); return np.maximum(img - b, 0)


def vivid(img, sat, con=1.0):
    y = lum(img)[..., None]
    if con != 1.0:
        mu = float(np.percentile(y, 99.0)) * 0.3 + 1e-4; img = img * (np.maximum(y, 1e-6) / mu) ** (con - 1) ; y = lum(img)[..., None]
    return np.maximum(y + (img - y) * sat, 0).astype(f32)


def ell_mask(h, w, cx, cy, a, b, pa_screen, seed, soft=0.5, rough=0.10):
    """soft noisy ellipse; a, b semi-axes in px; pa_screen = angle of the major axis on the sprite (rad, from +x)"""
    yy, xx = np.mgrid[0:h, 0:w].astype(f32)
    dx, dy = xx - cx, yy - cy; c, s = math.cos(pa_screen), math.sin(pa_screen)
    u = (dx * c + dy * s) / a; v = (-dx * s + dy * c) / b
    n = cv2.resize(fbm2((64, 64), seed, 2.4), (w, h), interpolation=cv2.INTER_CUBIC)
    r = np.sqrt(u * u + v * v) * (1 + rough * n)
    return smooth(1.0, soft, r).astype(f32)


def pa_dir(pa_deg):
    """direction of position angle pa (N through E) in sprite coords (x right = west, y down = south)"""
    p = math.radians(pa_deg); return -math.sin(p), -math.cos(p)


# ------------------------------------------------------------------------------------------------ M31 (GALEX)
def m31():
    img = load(os.path.join(DL, "andromeda_4K.png"))
    # measured in the 4K image (blurred peaks): nucleus, M32, M110
    P = np.array([[1733, 1110], [1184, 1028], [2199, 1819]], np.float64)
    Q = np.array([tan_off(*M31, *M31), tan_off(*M32, *M31), tan_off(*M110, *M31)], np.float64)
    # sprite frame: x = -E * K + cx, y = -N * K + cy
    w, h = SZ, SZ; cx, cy = w / 2, h / 2
    D = np.stack([-Q[:, 0] * K + cx, -Q[:, 1] * K + cy], 1)
    A = cv2.getAffineTransform(P.astype(f32), D.astype(f32))
    det = A[0, 0] * A[1, 1] - A[0, 1] * A[1, 0]
    print("m31 affine scale", math.sqrt(abs(det)), "det sign", np.sign(det), "rot deg", math.degrees(math.atan2(A[1, 0], A[0, 0])))
    img = blacklevel(img, 25)
    big = cv2.warpAffine(img, A, (w, h), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_CONSTANT)
    valid = cv2.warpAffine(np.ones(img.shape[:2], f32), A, (w, h), flags=cv2.INTER_LINEAR)
    valid = cv2.GaussianBlur(cv2.erode(valid, np.ones((5, 5), np.uint8)), (0, 0), 6)
    ax, ay = pa_dir(35.0); pa_s = math.atan2(ay, ax)
    m = ell_mask(h, w, cx, cy, 1.62 * K, 0.52 * K, pa_s, 31, 0.45, 0.06)
    big = vivid(big * (m * valid)[..., None], 2.6, 1.15)
    # the faint outer disc beyond the UV image (D25 = 3.17 x 1.0 deg): a soft exponential glow on the same axis
    yy, xx = np.mgrid[0:h, 0:w].astype(f32); dx, dy = xx - cx, yy - cy
    u = (dx * math.cos(pa_s) + dy * math.sin(pa_s)) / K; v = (-dx * math.sin(pa_s) + dy * math.cos(pa_s)) / K
    r = np.sqrt(u * u + (v / 0.31) ** 2)
    outer = (np.exp(-r / 0.55) * smooth(1.75, 1.3, r) * 0.24)[..., None] * np.array([0.55, 0.70, 1.0], f32)
    bul = (np.exp(-np.sqrt(u * u + (v / 0.6) ** 2) / 0.08) * 1.3 + np.exp(-np.sqrt(u * u + (v / 0.5) ** 2) / 0.25) * 0.25)[..., None] * np.array([1.0, 0.74, 0.34], f32)
    out = big + outer + bul
    return out, (cx, cy), np.maximum(m * valid, smooth(1.75, 1.2, r))



if __name__ == "__main__":
    img, c, m = m31()
    np.savez(os.path.join(SCR, "m31.npz"), img=img.astype(np.float16), c=np.array(c), K=K)
    a = np.asarray(img, f32); a = np.clip(1 - np.exp(-a * 2.0), 0, 1) ** (1 / 2.2)
    Image.fromarray((a * 255).astype(np.uint8)).resize((768, 768)).save(os.path.join(SCR, "pv_m31.jpg"))
    print("ok", img.shape, float(img.max()))
