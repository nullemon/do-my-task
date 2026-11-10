"""Type for Shorts: one big word at a time (orange, heavy dark outline, soft shadow, pop-in), and small HUD text.
All drawing is done on an sRGB RGBA PIL layer and composited after tone-mapping."""
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from .core import f32

FONT_DIR = "/usr/share/fonts/opentype/inter"
_fonts = {}
def font(sz, wt="Black", display=True):
    k = (int(sz), wt, display)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(f"{FONT_DIR}/{'InterDisplay' if display else 'Inter'}-{wt}.otf", int(sz))
    return _fonts[k]

ORANGE = (255, 146, 16)
ORANGE_HOT = (255, 168, 40)


def word_layer(word, size, maxw, fill=ORANGE, stroke=None, scale=1.0):
    """render one caption word -> RGBA uint8 numpy (tight box with padding), premultiplied-friendly"""
    sz = size * scale
    f = font(sz)
    w = f.getlength(word)
    if w > maxw * scale: f = font(sz * maxw * scale / w); w = f.getlength(word)
    sw = stroke or max(4, int(f.size * 0.085))
    pad = sw + int(f.size * 0.35)
    asc, desc = f.getmetrics()
    Wd, Hd = int(w + 2 * pad), int(asc + desc + 2 * pad)
    # soft shadow
    sh = Image.new("L", (Wd, Hd), 0)
    ImageDraw.Draw(sh).text((pad, pad + f.size * 0.06), word, font=f, fill=255, stroke_width=sw + 2, stroke_fill=255)
    sh = sh.filter(ImageFilter.GaussianBlur(f.size * 0.12))
    img = Image.new("RGBA", (Wd, Hd), (0, 0, 0, 0))
    img.paste((0, 0, 0, 255), (0, 0), sh.point(lambda v: int(v * 0.65)))
    d = ImageDraw.Draw(img)
    d.text((pad, pad), word, font=f, fill=(20, 10, 4, 255), stroke_width=sw, stroke_fill=(20, 10, 4, 255))
    # subtle vertical gradient in the fill (lighter top) for a less flat look
    fillm = Image.new("L", (Wd, Hd), 0); ImageDraw.Draw(fillm).text((pad, pad), word, font=f, fill=255)
    grad = np.linspace(1.10, 0.90, Hd)[:, None, None] * np.array(fill, f32)[None, None]
    grad = Image.fromarray(np.clip(np.broadcast_to(grad, (Hd, Wd, 3)), 0, 255).astype(np.uint8), "RGB")
    img.paste(grad, (0, 0), fillm)
    return np.asarray(img), (asc + desc) / 2 + pad


def composite(dst, rgba, cx, cy, alpha=1.0):
    """alpha-composite uint8 RGBA (straight) centred at (cx, cy) onto float sRGB dst (H, W, 3) 0..1"""
    h, w = rgba.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    H, W = dst.shape[:2]
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xb <= xa or yb <= ya: return
    src = rgba[ya - y0:yb - y0, xa - x0:xb - x0].astype(f32) / 255
    a = src[..., 3:] * alpha
    dst[ya:yb, xa:xb] = dst[ya:yb, xa:xb] * (1 - a) + src[..., :3] * a


class Captions:
    """words: list of dict(cap, t0, t1) in absolute seconds. One word on screen at a time."""
    def __init__(self, layout, words, emphasis=(), hold=0.35):
        self.L = layout; self.words = words; self.emph = set(emphasis)
        self.hold = hold; self._cache = {}

    def active(self, t):
        for i, w in enumerate(self.words):
            end = self.words[i + 1]["t0"] if i + 1 < len(self.words) else w["t1"] + 0.6
            end = min(end, w["t1"] + self.hold)
            if w["t0"] - 0.03 <= t < end: return i, w, end
        return None

    def draw(self, dst, t):
        a = self.active(t)
        if not a: return
        i, w, end = a
        age = t - (w["t0"] - 0.03)
        pop = 1.0 + 0.16 * np.exp(-age / 0.045) * (age < 0.25)        # quick pop-in
        big = 1.18 if w["cap"] in self.emph else 1.0
        fade = min(1.0, (end - t) / 0.06)
        key = (w["cap"], round(pop * big, 2))
        if key not in self._cache:
            self._cache[key] = word_layer(w["cap"], self.L.cap_size, self.L.cap_maxw, fill=ORANGE_HOT if big > 1 else ORANGE, scale=pop * big)
        rgba, _ = self._cache[key]
        composite(dst, rgba, self.L.W / 2, self.L.cap_y, fade)


def hud_text(dst, txt, cx, cy, size, wt="SemiBold", col=(240, 244, 250), alpha=1.0, track=0.06, shadow=True, display=False, anchor="c"):
    """small spaced text (labels, counters) on float sRGB dst"""
    f = font(size, wt, display)
    chars = list(txt)
    adv = [f.getlength(c) for c in chars]
    tw = sum(adv) + track * size * (len(chars) - 1)
    pad = int(size * 0.6)
    Wd, Hd = int(tw + 2 * pad), int(size * 1.5 + 2 * pad)
    lay = Image.new("RGBA", (Wd, Hd), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    sh = Image.new("L", (Wd, Hd), 0); ds = ImageDraw.Draw(sh)
    x = pad
    for c, a in zip(chars, adv):
        d.text((x, pad), c, font=f, fill=col + (255,)); ds.text((x, pad), c, font=f, fill=255)
        x += a + track * size
    out = Image.new("RGBA", (Wd, Hd), (0, 0, 0, 0))
    if shadow:
        sh = sh.filter(ImageFilter.GaussianBlur(size * 0.18)).point(lambda v: int(v * 0.8))
        out.paste((0, 0, 0, 255), (0, 0), sh)
    out.alpha_composite(lay)
    arr = np.asarray(out)
    if anchor == "l": cx = cx + Wd / 2 - pad
    elif anchor == "r": cx = cx - Wd / 2 + pad
    composite(dst, arr, cx, cy + size * 0.25, alpha)
    return tw
