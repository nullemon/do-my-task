"""Nebula sprites + sky star field for "What If Famous Nebulas Were in Our Sky?".
Each real image (NASA / NASA-ESA-CSA-STScI, via unit511/space-wallpapers; sources and licences in README) is cropped,
converted to linear light, black-levelled, given a soft noisy-edged mask and resampled to its TRUE on-screen size for the
premise (the nebula moved to D_REF = 15 ly, gnomonic lens f = 960 px, so a nebula D ly across is F*D/D_REF px wide).
The brightest embedded stars of each image are located so the renderer can make them twinkle.
Usage: /home/user/ttsenv/bin/python prep.py   -> SCR/sprites.npz"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, "..")]
import lib.core  # noqa: F401
import numpy as np, cv2
from PIL import Image
from lib.core import f32, srgb_to_lin, lum, fbm2, smooth

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S16-nebula-sky"
IMG = os.path.join(SCR, "dl", "img")
F_PX, D_REF = 960.0, 15.0


def px(D_ly): return F_PX * D_ly / D_REF        # gnomonic: 2 f tan(theta/2) with theta = 2 atan(D / 2d)


# key: file, crop box (fractions x0, y0, x1, y1), how many ly the crop's WIDTH spans (None: height given instead),
#      black-level percentile (None: no subtraction), mask ellipse radii (fractions of half-size), saturation
NEB = {
    "orion": dict(f="4K_orion_hearth_4K.png", crop=(0.0, 0.0, 1.0, 1.0), w_ly=24.0, bl=None, mask=(1.0, 1.0), sat=1.15),
    "ring":  dict(f="4K_webb_ring.png", crop=(0.0, 0.0, 1.0, 1.0), w_ly=1.0 * 3840 / 2900, bl=4, mask=(1.0, 1.15), sat=1.1),
    "pill":  dict(f="4K_webb_pillars.png", crop=(0.0, 0.0, 1.0, 1.0), h_ly=3400 / 3100 * 4.0, bl=None, mask=(0.95, 0.98), sat=1.1,
                 rot=(47.6, 2150, 1100, 2200, 3400)),   # turned upright: tallest pillar (~3100 px source) = 4 ly
    "crab":  dict(f="4K_crab_nebula_4K.png", crop=(0.0, 0.0, 1.0, 1.0), w_ly=11.5, bl=3, mask=(1.0, 1.05), sat=1.15),
    "car":   dict(f="4K_webb_carina_4K.png", crop=(0.0, 0.0, 1.0, 1.0), w_ly=None, bl=None, mask=None, sat=1.1),
}


def load(f, crop):
    im = Image.open(os.path.join(IMG, f)).convert("RGB")
    W, H = im.size
    x0, y0, x1, y1 = crop
    im = im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)))
    return srgb_to_lin(np.asarray(im, f32) / 255.0)


def soft_mask(h, w, rx, ry, seed):
    yy, xx = np.mgrid[0:h, 0:w].astype(f32)
    u = (xx - w / 2) / (w / 2 * rx); v = (yy - h / 2) / (h / 2 * ry)
    n = cv2.resize(fbm2((64, 64), seed, 2.4), (w, h), interpolation=cv2.INTER_CUBIC)
    r = np.sqrt(u * u + v * v) * (1 + 0.10 * n)
    return smooth(1.0, 0.55, r).astype(f32) ** 1.3


def find_stars(img, n=30):
    y = lum(img)
    hp = y - cv2.GaussianBlur(y, (0, 0), 3.0)
    mx = cv2.dilate(hp, np.ones((9, 9), np.uint8))
    pk = (hp >= mx) & (hp > np.percentile(hp, 99.7))
    ys, xs = np.nonzero(pk)
    v = hp[ys, xs]; o = np.argsort(-v)[:n]
    col = img[ys[o], xs[o]]; col = col / np.maximum(col.max(1, keepdims=True), 1e-4)
    return np.stack([xs[o], ys[o], v[o] / max(v[o].max(), 1e-6)], 1).astype(f32), col.astype(f32)


def main():
    out = {}
    for i, (k, c) in enumerate(NEB.items()):
        src = load(c["f"], c["crop"])
        valid = None
        if c.get("rot"):                                          # rotate about (cx, cy) into an ow x oh canvas
            a_, cx_, cy_, ow, oh = c["rot"]
            R = cv2.getRotationMatrix2D((cx_, cy_), a_, 1.0); R[0, 2] += ow / 2 - cx_; R[1, 2] += oh / 2 - cy_
            valid = cv2.warpAffine(np.ones(src.shape[:2], f32), R, (ow, oh), flags=cv2.INTER_LINEAR)
            src = cv2.warpAffine(src, R, (ow, oh), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT)
        sh, sw = src.shape[:2]
        if k == "car":                                            # all-sky backdrop: fixed large texture
            w = 2900; h = int(round(sh * w / sw))
        elif c.get("h_ly"):
            h = int(round(px(c["h_ly"]))); w = int(round(sw * h / sh))
        else:
            w = int(round(px(c["w_ly"]))); h = int(round(sh * w / sw))
        img = cv2.resize(src, (w, h), interpolation=cv2.INTER_AREA)
        if c["bl"] is not None:
            b = np.percentile(lum(img), c["bl"]); img = np.maximum(img - b, 0)
        y = lum(img)[..., None]; img = np.maximum(y + (img - y) * c["sat"], 0)
        if c["mask"] is not None:
            m = soft_mask(h, w, *c["mask"], seed=300 + i)
            if valid is not None: m = m * cv2.GaussianBlur(cv2.resize(valid, (w, h), interpolation=cv2.INTER_AREA), (0, 0), 3) ** 2
            img = img * m[..., None]
        else: m = np.ones((h, w), f32)
        st, sc = find_stars(img, {"ring": 6, "pill": 10}.get(k, 40))
        wgt = m[..., None]
        light = (img * wgt).sum((0, 1)) / max(wgt.sum(), 1)
        out[k] = img.astype(np.float16); out[k + "_m"] = m.astype(np.float16); out[k + "_st"] = st; out[k + "_sc"] = sc; out[k + "_light"] = light.astype(f32)
        print(k, (w, h), "light", np.round(light, 3), "stars", len(st))
    np.savez(os.path.join(SCR, "sprites.npz"), **out)


if __name__ == "__main__":
    main()
