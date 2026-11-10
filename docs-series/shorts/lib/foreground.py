"""Ground-level foreground plate: any RGBA PNG with a transparent sky.
 - placement for vertical (fit width, bottom aligned) or 16:9 (fit width, crop so the horizon sits at `hz_frac`)
 - Lanczos resize of premultiplied colour, light unsharp mask, 1 px alpha erosion, edge colour decontamination
 - horizon auto-detected from alpha (first row that is opaque across ~all columns), skyline per column
 - relighting states (all linear HDR, same size as the frame):
     day()                      the photo as shot
     night(level)               starlight only: daylight shadows flattened out, desaturated, cold blue grade
     frost(img, amount, t)      creeping blue-white crystalline frost + glints
     lamps(img, on, t)          warm street-lamp heads + light pools (positions = config list in SOURCE pixels)
"""
import os, math
import numpy as np, cv2
from PIL import Image
from .core import f32, srgb_to_lin, lum, smooth, fbm2, noise1, CACHE, splat


class Foreground:
    def __init__(self, path, layout, lamps=(), hz_frac=0.66, sharpen=0.35, horizon_src=None):
        self.L = layout; W, H = layout.W, layout.H
        im = np.asarray(Image.open(path).convert("RGBA"), f32) / 255.0
        sh, sw = im.shape[:2]
        s = W / sw
        if layout.vertical:
            oy = H - sh * s                                     # bottom aligned (sky padding on top if short)
        else:
            hz0 = self._horizon(im[..., 3]) if horizon_src is None else horizon_src
            oy = hz_frac * H - hz0 * s
        self.s, self.oy = s, oy
        # premultiplied Lanczos resize into the frame
        M = np.array([[s, 0, 0], [0, s, oy]], np.float64)
        pre = np.concatenate([im[..., :3] * im[..., 3:], im[..., 3:]], 2)
        out = cv2.warpAffine(pre, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        if not layout.vertical:                                 # rows below the source bottom: replicate last row
            yb = int(math.floor(sh * s + oy)) - 2
            if yb < H: out[yb:] = out[yb - 1:yb]
        a = np.clip(out[..., 3], 0, 1)
        rgb = np.clip(out[..., :3] / np.maximum(a, 1e-4)[..., None], 0, 1)
        if sharpen > 0:
            bl = cv2.GaussianBlur(rgb, (0, 0), 1.1)
            rgb = np.clip(rgb + sharpen * (rgb - bl), 0, 1)
        # 1 px erosion of the alpha (kills light fringes against a dark sky), softened back by half a pixel
        a = np.minimum(a, cv2.GaussianBlur(cv2.erode(a, np.ones((3, 3), np.uint8)), (0, 0), 0.5))
        # decontaminate edge colour: pull colour in from fully opaque neighbours
        solid = (a > 0.985).astype(f32)
        num = cv2.GaussianBlur(rgb * solid[..., None], (0, 0), 2.0); den = cv2.GaussianBlur(solid, (0, 0), 2.0)
        inner = num / np.maximum(den, 1e-4)[..., None]
        wedge = np.clip((0.985 - a) / 0.6, 0, 1)[..., None] * (den > 0.02)[..., None]
        rgb = rgb * (1 - wedge) + inner * wedge
        self.a = a.astype(f32)
        self.rgb = srgb_to_lin(rgb)
        self.horizon = self._horizon(self.a)
        col = self.a > 0.5
        self.skyline = np.where(col.any(0), col.argmax(0), H).astype(f32)
        self.lamps = [(x * s, y * s + oy) for (x, y) in lamps]
        self._prep()

    @staticmethod
    def _horizon(a):
        """first row (from the top) where >= 97 % of columns are opaque"""
        frac = (a > 0.5).mean(1)
        rows = np.where(frac >= 0.97)[0]
        return float(rows[0]) if len(rows) else float(a.shape[0] * 0.75)

    def _prep(self):
        W, H = self.L.W, self.L.H
        a = self.a; rgb = self.rgb
        yy = np.arange(H, dtype=f32)[:, None] * np.ones((1, W), f32)
        self.ground = (smooth(self.horizon - 10, self.horizon + 40, yy) * (a > 0.5)).astype(f32)
        # shadow flattening: divide out the low-frequency luminance (alpha-aware), restore the regional mean
        Y = lum(rgb)
        sig = 14 * self.s
        num = cv2.GaussianBlur(Y * a, (0, 0), sig); den = cv2.GaussianBlur(a, (0, 0), sig)
        lo = num / np.maximum(den, 1e-3)
        gmask = self.ground > 0.5
        g_ref = np.percentile(lo[gmask], 70) if gmask.any() else lo.mean()
        t_ref = np.percentile(lo[(a > 0.5) & ~gmask], 60) if ((a > 0.5) & ~gmask).any() else g_ref
        ref = g_ref * self.ground + t_ref * (1 - self.ground)
        gain = np.clip(ref / np.maximum(lo, 1e-4), 0.4, 4.0)
        k = (0.95 * self.ground + 0.55 * (1 - self.ground))           # flatten fully on the lawn, half on foliage
        self.flat = (rgb * (1 + (gain - 1) * k)[..., None]).astype(f32)
        # frost fields
        r = np.random.default_rng(11)
        n_lo = cv2.resize(fbm2((256, 256), 21, 2.4), (W, H), interpolation=cv2.INTER_CUBIC)
        fine = fbm2((H, W), 22, 0.9)
        streak = np.zeros((H, W), f32)
        for ang in (0, 60, 120):                                        # feathery hexagonal-ish crystal streaks
            k_ = cv2.getRotationMatrix2D((7, 7), ang, 1.0); ker = np.zeros((15, 15), f32); ker[7, :] = 1
            ker = cv2.warpAffine(ker, k_, (15, 15)); ker /= ker.sum()
            streak += cv2.filter2D(fine, -1, ker)
        self.crystal = np.clip(0.55 + 0.35 * streak + 0.25 * fine, 0, 1.6).astype(f32)
        # frost front: starts at the near lawn and the tops of things, creeps up and back
        up = 1 - yy / H
        edge = np.clip(a - cv2.erode(a, np.ones((5, 5), np.uint8)), 0, 1)
        self.frost_front = (0.62 * up + 0.22 * n_lo * 0.5 - 0.25 * edge).astype(f32)
        self.frost_cover = (0.95 * self.ground + 0.70 * (1 - self.ground) * smooth(0.02, 0.2, Y)).astype(f32) * a
        # glints: random points on frosted surfaces
        idx = np.flatnonzero((self.frost_cover > 0.4).ravel())
        pick = r.choice(idx, min(len(idx), 5000), replace=False)
        self.glint_xy = np.stack([pick % W, pick // W], 1).astype(np.int32)
        self.glint_ph = r.uniform(0, 6.283, len(pick)).astype(f32)
        self.glint_fr = r.uniform(0.5, 3.0, len(pick)).astype(f32)
        self.glint_sz = r.uniform(0.3, 1.0, len(pick)).astype(f32) ** 2

    # ----------------------------------------------------------------------------------------------- states
    def day(self, gain=1.0):
        return self.rgb * gain

    def night(self, level=1.0):
        """starlit: no directional light, no shadows; scotopic desaturation, cold blue grade"""
        f = self.flat
        y = lum(f)[..., None]
        n = f * 0.25 + y * 0.75
        n = n * np.array([0.50, 0.72, 1.25], f32)
        # slightly darker towards the bottom of frame (no skylight occlusion modelling; keeps the eye on the sky)
        H = self.L.H
        v = (1.0 - 0.25 * smooth(self.horizon, H, np.arange(H, dtype=f32)))[:, None, None]
        return (n * v * level).astype(f32)

    def frost(self, img, amount, t, level=1.0):
        """blend creeping frost into the (night) foreground image"""
        if amount <= 0: return img
        thr = amount * 1.35 - 0.25
        m = smooth(-0.06, 0.06, thr - self.frost_front) * self.frost_cover
        m = m * (0.55 + 0.45 * smooth(0.0, 1.0, amount))
        base = lum(self.flat)[..., None]
        fcol = (0.22 + 0.55 * base / (base + 0.12)) * self.crystal[..., None] * np.array([0.62, 0.78, 1.15], f32) * level
        out = img * (1 - m[..., None] * 0.85) + fcol * m[..., None]
        # glints (sparkle as starlight / lamplight catches ice facets)
        g = self.glint_xy
        mg = m[g[:, 1], g[:, 0]]
        tw = np.clip(np.sin(t * self.glint_fr * 6.283 + self.glint_ph), 0, 1) ** 12
        val = mg * tw * self.glint_sz * 3.0 * level
        sel = val > 0.01
        if sel.any():
            lay = np.zeros(img.shape[:2], f32)
            np.add.at(lay, (g[sel, 1], g[sel, 0]), val[sel])
            lay = cv2.GaussianBlur(lay, (0, 0), 0.8) * 4 + cv2.GaussianBlur(lay, (0, 0), 2.5) * 2
            out = out + lay[..., None] * np.array([0.8, 0.9, 1.0], f32)
        return out.astype(f32)

    def lamps_light(self, img, on, t, col=(1.0, 0.62, 0.30), pools=True):
        """add lamp heads + warm pools on the ground. `on` 0..1 (warm-up)."""
        if on <= 0 or not self.lamps: return img
        col = np.array(col, f32)
        out = img.copy()
        alb = np.clip(self.flat, 0, 1)
        for i, (lx, ly) in enumerate(self.lamps):
            fl = on * (1 + 0.03 * noise1(t, 40 + i, 9.0))
            if pools:
                # ground point below the head: first lawn row under the lamp
                gy = self.horizon + 0.10 * (self.L.H - self.horizon) * 0.4 + (ly - self.horizon) * -0.0
                xs = int(np.clip(lx, 0, self.L.W - 1))
                colg = np.where(self.ground[:, xs] > 0.5)[0]
                gy = float(colg[colg > ly][0]) + 4 * self.s if (colg > ly).any() else self.horizon
                h = gy - ly
                rx, ry = h * 1.1, h * 0.22
                y0, y1 = int(max(0, ly - 4)), int(min(self.L.H, gy + ry * 3))
                x0, x1 = int(max(0, lx - rx * 3)), int(min(self.L.W, lx + rx * 3))
                if y1 > y0 and x1 > x0:
                    yy, xx = np.mgrid[y0:y1, x0:x1].astype(f32)
                    d2 = ((xx - lx) / rx) ** 2 + ((yy - gy) / ry) ** 2
                    pool = np.exp(-d2 * 1.2) * self.ground[y0:y1, x0:x1]
                    # the pole and nearby foliage catch a little light from above
                    near = np.exp(-(((xx - lx) / (rx * 0.6)) ** 2 + ((yy - ly) / (h * 0.9)) ** 2)) * (1 - self.ground[y0:y1, x0:x1]) * self.a[y0:y1, x0:x1]
                    out[y0:y1, x0:x1] += alb[y0:y1, x0:x1] * col * ((pool * 1.6 + near * 0.35) * fl)[..., None]
            r = 3.2 * self.s
            splat(out, lx, ly + r * 0.6, r * 60, lambda d, dx, dy: (
                (np.clip(r - d + 0.5, 0, 1) * 40.0 + np.exp(-d / (r * 1.6)) * 4.0 + np.exp(-d / (r * 8)) * 0.35 + np.exp(-d / (r * 25)) * 0.05) * fl
            )[..., None] * col)
        return out
