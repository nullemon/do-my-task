"""Shared helpers for the numpy compositor (python3 + numpy + PIL)."""
import os, json, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 24
HERE = os.path.dirname(os.path.abspath(__file__))
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/05-mariana-trench"
PL = os.path.join(SCR, "plates")
TEX = os.path.join(SCR, "tex")
SEG = os.path.join(SCR, "seg")
FONT_L = "/usr/share/fonts/opentype/inter/Inter-Light.otf"
FONT_XL = "/usr/share/fonts/opentype/inter/Inter-ExtraLight.otf"
PLACE = json.load(open(os.path.join(HERE, "audio", "placement.json")))
LINES = PLACE["lines"]


def LS(i):
    return LINES[i]["start"]


def LE(i):
    return LINES[i]["end"]


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def ss(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


# ------------------------------------------------------------------ filters
def box1(a, r, axis):
    r = int(r)
    if r < 1:
        return a
    n = a.shape[axis]
    pad = [(0, 0)] * a.ndim; pad[axis] = (r, r)
    p = np.pad(a, pad, mode="edge")
    def sl(k):
        return tuple(slice(k, k + n) if i == axis else slice(None) for i in range(a.ndim))
    if r <= 4:
        out = p[sl(0)].astype(np.float32, copy=True)
        for k in range(1, 2 * r + 1):
            out += p[sl(k)]
        return out * np.float32(1.0 / (2 * r + 1))
    c = np.cumsum(p, axis=axis, dtype=np.float32)
    zshape = list(c.shape); zshape[axis] = 1
    c = np.concatenate([np.zeros(zshape, np.float32), c], axis=axis)
    hi = tuple(slice(2 * r + 1, 2 * r + 1 + n) if i == axis else slice(None) for i in range(a.ndim))
    lo = tuple(slice(0, n) if i == axis else slice(None) for i in range(a.ndim))
    return (c[hi] - c[lo]) * np.float32(1.0 / (2 * r + 1))


def blur(a, r, passes=3):
    rr = max(1, int(round(r / math.sqrt(passes))))
    for _ in range(passes):
        a = box1(box1(a, rr, 0), rr, 1)
    return a


def down4(a):
    h, w = a.shape[:2]
    return a.reshape(h // 4, 4, w // 4, 4, *a.shape[2:]).mean(axis=(1, 3))


def up4(a):
    h, w = a.shape[:2]
    if a.ndim == 2:
        return np.asarray(Image.fromarray(np.ascontiguousarray(a, np.float32), "F").resize((w * 4, h * 4), Image.BILINEAR))
    return np.stack([np.asarray(Image.fromarray(np.ascontiguousarray(a[..., c], np.float32), "F")
                                .resize((w * 4, h * 4), Image.BILINEAR)) for c in range(a.shape[2])], -1)


def zoom_crop_ch(chans, z, cx, cy):
    """Fast PIL bilinear crop/zoom of a list of 2D float32 channel images (same geometry as zoom_crop)."""
    hp, wp = chans[0].shape
    hw = wp / z / 2; hh = hw * H / W
    box = (cx - hw, cy - hh, cx + hw, cy + hh)
    return np.stack([np.asarray(Image.fromarray(c, "F").transform((W, H), Image.EXTENT, box, Image.BILINEAR))
                     for c in chans], -1)


def bloom(lin, strength=0.6, r=14, thresh=0.0):
    d = down4(lin)
    if thresh > 0:
        d = np.maximum(d - thresh, 0)
    b1 = blur(d, r / 4 * 1.0)
    b2 = blur(d, r)
    return lin + strength * up4(0.6 * b1 + 0.4 * b2)


def tonemap(lin, exposure=1.0):
    return 1.0 - np.exp(-np.maximum(lin, 0) * exposure)


_LUT = (np.linspace(0, 1, 4097) ** (1 / 2.2) * 255 + 0.5).astype(np.uint8)


def to8(disp):
    return _LUT[(np.clip(disp, 0, 1) * 4096).astype(np.int32)]


def srgb_to_lin(img8):
    return (img8.astype(np.float32) / 255.0) ** 2.2


# ------------------------------------------------------------------ sampling
def zoom_crop(plate, z, cx, cy):
    """Axis-aligned bilinear crop/zoom of a plate (Hp,Wp,C) to (H,W,C).
    z=1 shows the full plate width; (cx, cy) = centre in plate pixel coords."""
    hp, wp = plate.shape[:2]
    sx = wp / W / z
    xs = cx + (np.arange(W, dtype=np.float32) + 0.5 - W / 2) * sx - 0.5
    ys = cy + (np.arange(H, dtype=np.float32) + 0.5 - H / 2) * sx - 0.5
    xs = np.clip(xs, 0, wp - 1.001); ys = np.clip(ys, 0, hp - 1.001)
    x0 = xs.astype(np.int32); y0 = ys.astype(np.int32)
    fx = (xs - x0)[None, :, None]; fy = (ys - y0)[:, None, None]
    r0 = plate[y0]; r1 = plate[y0 + 1]
    a = r0[:, x0].astype(np.float32); b = r0[:, x0 + 1].astype(np.float32)
    c = r1[:, x0].astype(np.float32); d = r1[:, x0 + 1].astype(np.float32)
    top = a + (b - a) * fx; bot = c + (d - c) * fx
    return top + (bot - top) * fy


def clamp_center(plate_shape, z, cx, cy):
    hp, wp = plate_shape[:2]
    hw = wp / z / 2; hh = hw * H / W
    return min(max(cx, hw), wp - hw), min(max(cy, hh), hp - hh)


def bilinear_wrap(tex, x, y):
    """Sample a periodic 2D (or HxWxC) texture at float coords with wrap."""
    h, w = tex.shape[:2]
    x0 = np.floor(x).astype(np.int32); y0 = np.floor(y).astype(np.int32)
    fx = x - x0; fy = y - y0
    x0 %= w; y0 %= h; x1 = (x0 + 1) % w; y1 = (y0 + 1) % h
    if tex.ndim == 3:
        fx = fx[..., None]; fy = fy[..., None]
    a = tex[y0, x0]; b = tex[y0, x1]; c = tex[y1, x0]; d = tex[y1, x1]
    return (a + (b - a) * fx) * (1 - fy) + (c + (d - c) * fx) * fy


def periodic_noise(n=1024, beta=2.6, seed=0, kmin=2.0):
    r = np.random.default_rng(seed)
    wn = r.standard_normal((n, n)).astype(np.float32)
    f = np.fft.fftfreq(n) * n
    kx, ky = np.meshgrid(f, f)
    k = np.sqrt(kx ** 2 + ky ** 2)
    amp = np.where(k < kmin, 0, (k + 1e-6) ** (-beta / 2))
    out = np.real(np.fft.ifft2(np.fft.fft2(wn) * amp)).astype(np.float32)
    return (out - out.mean()) / out.std()


# ------------------------------------------------------------------ splatting
class Acc:
    """Additive point accumulation buffer (bilinear splats via bincount)."""
    def __init__(self, w=W, h=H):
        self.w, self.h = w, h
        self.buf = np.zeros((3, h * w), np.float32)

    def add(self, x, y, wgt, col):
        x = np.asarray(x, np.float32); y = np.asarray(y, np.float32)
        wgt = np.broadcast_to(np.asarray(wgt, np.float32), x.shape).ravel()
        x = x.ravel(); y = y.ravel()
        col = np.asarray(col, np.float32)
        if col.ndim == 1:
            col = np.broadcast_to(col, (x.size, 3))
        else:
            col = col.reshape(-1, 3)
        ok = (x >= 0) & (x < self.w - 1) & (y >= 0) & (y < self.h - 1) & (wgt > 0)
        x, y, wgt, col = x[ok], y[ok], wgt[ok], col[ok]
        if x.size == 0:
            return
        x0 = x.astype(np.int32); y0 = y.astype(np.int32)
        fx = x - x0; fy = y - y0
        n = self.w * self.h
        base = y0 * self.w + x0
        idx = np.concatenate([base, base + 1, base + self.w, base + self.w + 1])
        ww = np.concatenate([(1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy]) * np.tile(wgt, 4)
        for c in range(3):
            self.buf[c] += np.bincount(idx, weights=ww * np.tile(col[:, c], 4), minlength=n).astype(np.float32)

    def image(self):
        return self.buf.reshape(3, self.h, self.w).transpose(1, 2, 0)


def segments(x0, y0, x1, y1, n=8):
    t = np.linspace(0, 1, n, dtype=np.float32)[None, :]
    return (x0[:, None] + (x1 - x0)[:, None] * t), (y0[:, None] + (y1 - y0)[:, None] * t)


# ------------------------------------------------------------------ text
_TXT = {}


def text_alpha(s, size, tracking=0.30, font=FONT_L):
    key = (s, size, tracking, font)
    if key in _TXT:
        return _TXT[key]
    f = ImageFont.truetype(font, size * 2)
    sp = tracking * size * 2
    widths = [f.getlength(ch) for ch in s]
    tw = int(sum(widths) + sp * (len(s) - 1)) + 8
    asc, desc = f.getmetrics()
    im = Image.new("L", (tw, asc + desc + 8), 0)
    d = ImageDraw.Draw(im)
    x = 4
    for ch, wch in zip(s, widths):
        d.text((x, 4), ch, font=f, fill=255)
        x += wch + sp
    im = im.resize((max(1, tw // 2), max(1, (asc + desc + 8) // 2)), Image.LANCZOS)
    a = np.asarray(im, np.float32) / 255.0
    _TXT[key] = a
    return a


def draw_text(disp, s, cx, cy, size, op=1.0, col=(0.93, 0.92, 0.88), tracking=0.30, font=FONT_L, anchor="c"):
    if op <= 0.003:
        return
    a = text_alpha(s, size, tracking, font)
    h, w = a.shape
    x0 = int(round(cx - w / 2)) if anchor == "c" else (int(round(cx)) if anchor == "l" else int(round(cx - w)))
    y0 = int(round(cy - h / 2))
    xa, ya = max(0, x0), max(0, y0)
    xb, yb = min(W, x0 + w), min(H, y0 + h)
    if xb <= xa or yb <= ya:
        return
    al = a[ya - y0:yb - y0, xa - x0:xb - x0][..., None] * op
    reg = disp[ya:yb, xa:xb]
    # soft dark halo for legibility
    disp[ya:yb, xa:xb] = reg * (1 - al) + np.asarray(col, np.float32) * al


def caption(disp, t, t0, t1, main, sub=None, y=None, size=30, fade=0.6):
    op = ss(t0, t0 + fade, t) * (1 - ss(t1 - fade, t1, t))
    if op <= 0:
        return
    y = H * 0.875 if y is None else y
    # subtle dark band behind for legibility on bright shots
    y0b, y1b = int(y - 90), int(y + (120 if sub else 90))
    yy = np.arange(y0b, y1b, dtype=np.float32)
    yc = y + (20 if sub else 0)
    g = np.exp(-((yy - yc) / 55.0) ** 2)[:, None, None]
    disp[y0b:y1b] *= (1 - 0.35 * op * g)
    draw_text(disp, main, W / 2, y, size, op)
    if sub:
        draw_text(disp, sub, W / 2, y + size * 1.35, int(size * 0.62), op * 0.85, tracking=0.34)


# ------------------------------------------------------------------ writer
class Writer:
    def __init__(self, name, crf=16):
        os.makedirs(SEG, exist_ok=True)
        self.path = os.path.join(SEG, name + ".mp4")
        self.tmp = self.path + ".part.mp4"
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                   "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                                   "-preset", "fast", "-crf", str(crf), "-pix_fmt", "yuv420p", self.tmp],
                                  stdin=subprocess.PIPE)
        self.n = 0

    def write(self, img8):
        self.p.stdin.write(np.ascontiguousarray(img8).tobytes()); self.n += 1

    def close(self):
        self.p.stdin.close(); self.p.wait()
        os.replace(self.tmp, self.path)
        return self.n
