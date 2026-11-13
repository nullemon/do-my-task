"""python lib/render.py <code> V|H [options]
  ONLY=3,7,12   re-render just these spans          RESUME=1  skip spans already rendered
  PREVIEW=30    render only spans that start before 30 s
  STILLS=3.0,22.5  write preview JPGs at these global times (no video)
  JOBS=n        parallel workers (default: CPU cores - 1)
One .mp4 per span in work/out_<F>/sNNN.mp4 (written to .tmp.mp4 and renamed on success). Crossfades live inside each span.
"""
import os, sys, json, math, re, subprocess, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_case, font, MB, MXB, MSB, MM, PF, PFB, FPS, FF, video_encoder, probe_wh
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageEnhance, ImageChops

GOLD = (255, 205, 60); WHITE = (255, 255, 255); RED = (225, 38, 45); INK = (14, 14, 16)
CFG = SCR = TL = None; FMT = "V"; W = H = 0; G = {}

def setup(code, fmt):
    global CFG, SCR, TL, FMT, W, H, G
    CFG, SCR = load_case(code); FMT = fmt
    W, H = (1080, 1920) if fmt == "V" else (1920, 1080)
    TL = json.load(open(os.path.join(CFG.WORK, "timeline.json"), encoding="utf-8"))
    if fmt == "V":
        G = dict(head=300, cap_y=1500, cap_cx=505, cap_w=880, cap_size=70, safe_r=950,
                 split=(300, 1000, 1190, 1920), freeze=(300, 1290), board=(300, 1920))
    else:
        G = dict(head=0, cap_y=900, cap_cx=960, cap_w=1500, cap_size=60, safe_r=1900,
                 split=(0, 1150, 1150, 1920), freeze=(0, 1240), board=(0, 1080))

def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def eout(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3
def back(x):  # pop-in overshoot
    x = max(0.0, min(1.0, x)); c = 1.70158; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2

# ------------------------------------------------------------------ textures (cached)
_cache = {}
def noise_tex(w, h, base, amp, seed=1, blur=0.0):
    k = ("noise", w, h, base, amp, seed, blur)
    if k not in _cache:
        rng = np.random.default_rng(seed)
        n = rng.normal(0, amp, (h // 2 + 1, w // 2 + 1))
        im = Image.fromarray(np.clip(n + 128, 0, 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
        if blur: im = im.filter(ImageFilter.GaussianBlur(blur))
        a = np.asarray(im, np.float32)[..., None] - 128
        col = np.clip(np.array(base, np.float32)[None, None] + a, 0, 255).astype(np.uint8)
        _cache[k] = Image.fromarray(col)
    return _cache[k].copy()

def panel_tex(w, h, seed=3):
    """dark charcoal panel with fine grain + soft vignette (never flat)"""
    k = ("panel", w, h, seed)
    if k not in _cache:
        im = noise_tex(w, h, (24, 22, 22), 9, seed)
        big = noise_tex(w, h, (0, 0, 0), 14, seed + 7, blur=30)
        im = ImageChops.add(im, big, 1.0, -0)  # subtle mottling
        d = ImageDraw.Draw(im)
        for x in range(-h, w, 22): d.line([(x, 0), (x + h, h)], fill=(40, 37, 37), width=2)   # fine diagonal weave
        _cache[k] = im
    return _cache[k].copy()

def cork(w, h):
    k = ("cork", w, h)
    if k not in _cache:
        rng = np.random.default_rng(5)
        base = noise_tex(w, h, (150, 108, 68), 20, 11)
        a = np.asarray(base, np.int16)
        spots = rng.random((h, w)) < 0.02
        a[spots] -= 45
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
        mott = np.asarray(noise_tex(w, h, (0, 0, 0), 25, 13, blur=40), np.int16)[..., :1]
        a = np.clip(np.asarray(im, np.int16) + mott - 6, 0, 255).astype(np.uint8)
        _cache[k] = Image.fromarray(a)
    return _cache[k].copy()

_grain = None
def grain_layer(seed):
    global _grain
    if _grain is None:
        rng = np.random.default_rng(99)
        _grain = [Image.fromarray(np.clip(rng.normal(128, 18, (H // 2, W // 2)), 0, 255).astype(np.uint8)).resize((W, H), Image.NEAREST) for _ in range(6)]
    return _grain[seed % 6]

# ------------------------------------------------------------------ media sources
def tone_photo(im, tone):
    if tone == "none": return im
    g = im.convert("L")
    st = np.asarray(im.convert("RGB"), np.int16); sat = np.abs(st[..., 0] - st[..., 1]).mean() + np.abs(st[..., 1] - st[..., 2]).mean()
    if tone == "sepia" or (tone is None and sat < 12):     # black & white archive photo -> warm archival tone, gentle contrast
        g = ImageOps.autocontrast(g, cutoff=1)
        return ImageOps.colorize(g, (22, 18, 14), (250, 238, 214), mid=(150, 128, 100))
    im = ImageEnhance.Color(im).enhance(1.12); return ImageEnhance.Contrast(im).enhance(1.05)

class PhotoSrc:
    def __init__(self, m, bw, bh):
        ph = CFG.PH[m["key"]]
        im = Image.open(ph["file"]).convert("RGB")
        if m.get("crop"): im = im.crop(tuple(m["crop"]))
        im = tone_photo(im, m.get("tone"))
        self.credit = m.get("credit") or ph["credit"]
        z1 = max(m["z"]); s = max(bw / im.width, bh / im.height) * z1
        tw, th = int(im.width * s + 2), int(im.height * s + 2)
        big = im.resize((tw, th), Image.LANCZOS)
        if s > 1.6: big = big.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
        self.big = big; self.bw, self.bh = bw, bh; self.m = dict(m); self.s = s / z1
        if bw > bh and im.height > im.width * 0.95 and not m.get("pan"):   # portrait photo in a wide box: keep the face in frame
            fx, fy = m["focus"]; self.m["focus"] = (fx, fy * 0.62)
        self.sw, self.sh = im.width, im.height
    def frame(self, lt, dur):
        m = self.m; z = m["z"][0] + (m["z"][1] - m["z"][0]) * ease(lt / max(dur, 0.1)) if dur > 0 else m["z"][0]
        fx, fy = m["focus"]
        if m.get("pan"):
            (ax, ay), (bx, by) = m["pan"]; e = ease(lt / max(dur, 0.1)); fx, fy = ax + (bx - ax) * e, ay + (by - ay) * e
        z1 = max(m["z"]); cw, ch = self.bw * z1 / z, self.bh * z1 / z      # window in big-image pixels
        x0 = min(max(0, fx * self.big.width - cw / 2), self.big.width - cw); y0 = min(max(0, fy * self.big.height - ch / 2), self.big.height - ch)
        img = self.big.resize((self.bw, self.bh), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
        k = self.bw / cw   # big px -> panel px
        sc = self.big.width / self.sw
        self.map = lambda u, v: ((u * self.sw * sc - x0) * k, (v * self.sh * sc - y0) * k)
        return img

class VideoSrc:
    def __init__(self, m, bw, bh, dur):
        path = CFG.SRC[m["src"]]
        sw, sh = probe_wh(path)
        c = m.get("crop") or {}
        x0, y0, x1, y1 = c.get("x0", 0), c.get("y0", 0), min(sw, c.get("x1", sw)), min(sh, c.get("y1", sh))
        cw, ch = (x1 - x0) // 2 * 2, (y1 - y0) // 2 * 2
        z1 = max(m["z"]); s = max(bw / cw, bh / ch) * z1
        self.tw, self.th = int(cw * s / 2 + 1) * 2, int(ch * s / 2 + 1) * 2
        t_in = m["t_in"]; t_out = m.get("t_out") or (t_in + dur)
        self.p = subprocess.Popen([FF, "-loglevel", "error", "-ss", f"{max(0, t_in):.3f}", "-t", f"{max(0.1, t_out - t_in):.3f}", "-i", path,
                                   "-vf", f"crop={cw}:{ch}:{x0}:{y0},scale={self.tw}:{self.th}:flags=lanczos,fps={FPS}",
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.last = Image.new("RGB", (self.tw, self.th), (20, 20, 20)); self.m = m; self.bw, self.bh = bw, bh
        self.credit = m.get("credit") or CFG.SRC_CREDIT.get(m["src"], "")
        self.frozen = False; self.sw, self.sh = cw, ch
    def frame(self, lt, dur):
        if not self.frozen:
            b = self.p.stdout.read(self.tw * self.th * 3)
            if len(b) == self.tw * self.th * 3: self.last = Image.frombytes("RGB", (self.tw, self.th), b)
        m = self.m; z = m["z"][0] + (m["z"][1] - m["z"][0]) * ease(lt / max(dur, 0.1)); z1 = max(m["z"])
        cw, ch = self.bw * z1 / z, self.bh * z1 / z; fx, fy = m["focus"]
        x0 = min(max(0, fx * self.tw - cw / 2), self.tw - cw); y0 = min(max(0, fy * self.th - ch / 2), self.th - ch)
        k = self.bw / cw
        self.map = lambda u, v: ((u * self.tw - x0) * k, (v * self.th - y0) * k)
        return self.last.resize((self.bw, self.bh), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
    def close(self):
        try: self.p.kill()
        except Exception: pass

def make_src(m, bw, bh, dur):
    return PhotoSrc(m, bw, bh) if m["m"] == "photo" else VideoSrc(m, bw, bh, dur)

# ------------------------------------------------------------------ drawing helpers
def tlen(d, s, f): return d.textlength(s, font=f)
def fit_font(d, txt, name, size, maxw, minsize=10):
    f = font(name, size)
    while tlen(d, txt, f) > maxw and size > minsize: size -= 2; f = font(name, size)
    return f

def text_c(d, cx, y, txt, f, fill, stroke=0, sfill=INK, spacing=0):
    if spacing:
        ws = [tlen(d, c, f) for c in txt]; tw = sum(ws) + spacing * (len(txt) - 1); x = cx - tw / 2
        for c, cw in zip(txt, ws): d.text((x, y), c, font=f, fill=fill, stroke_width=stroke, stroke_fill=sfill); x += cw + spacing
        return tw
    tw = tlen(d, txt, f); d.text((cx - tw / 2, y), txt, font=f, fill=fill, stroke_width=stroke, stroke_fill=sfill); return tw

def wrap(d, txt, f, maxw):
    out, cur = [], ""
    for w in txt.split():
        t = (cur + " " + w).strip()
        if tlen(d, t, f) <= maxw or not cur: cur = t
        else: out.append(cur); cur = w
    if cur: out.append(cur)
    return out

def balanced(d, words, f, maxw):
    """split into <=2 lines with similar widths"""
    full = " ".join(words)
    if tlen(d, full, f) <= maxw * 0.62 or len(words) < 3: return [words]
    best = None
    for k in range(1, len(words)):
        a, b = " ".join(words[:k]), " ".join(words[k:])
        wa, wb = tlen(d, a, f), tlen(d, b, f); sc = max(wa, wb)
        if best is None or sc < best[0]: best = (sc, k)
    return [words[:best[1]], words[best[1]:]]

def gradient(w, h, top_a, bot_a, col=(0, 0, 0)):
    k = ("grad", w, h, top_a, bot_a, col)
    if k not in _cache:
        a = np.linspace(top_a, bot_a, h)[:, None].repeat(w, 1)
        a = (np.clip(a, 0, 1) ** 1.0 * 255).astype(np.uint8)
        L = Image.new("RGBA", (w, h), col + (0,)); L.putalpha(Image.fromarray(a)); _cache[k] = L
    return _cache[k]

def chip(canvas, x, y, txt, size=30, bg=RED, fg=WHITE, alpha=1.0, dot=False):
    d = ImageDraw.Draw(canvas, "RGBA"); f = font(MXB, size); tw = tlen(d, txt, f)
    pad = int(size * 0.55); hgt = int(size * 1.55); extra = int(size * 0.8) if dot else 0
    d.rounded_rectangle([x, y, x + tw + 2 * pad + extra, y + hgt], int(size * 0.35), fill=bg + (int(235 * alpha),))
    if dot: d.ellipse([x + pad, y + hgt / 2 - size * 0.2, x + pad + size * 0.4, y + hgt / 2 + size * 0.2], fill=(255, 60, 60, int(255 * alpha)))
    d.text((x + pad + extra, y + (hgt - size) / 2 - size * 0.12), txt, font=f, fill=fg + (int(255 * alpha),))
    return tw + 2 * pad + extra

def credit_line(canvas, x, y, txt, size=None, right=None):
    if not txt: return
    size = size or (22 if FMT == "V" else 20)
    d = ImageDraw.Draw(canvas, "RGBA"); f = font(MM, size); s = "Source: " + txt
    maxw = (right or (G["safe_r"] if FMT == "V" else W - 40)) - x
    if tlen(d, s, f) > maxw: f = fit_font(d, s, MM, size, maxw, 12)
    tw = tlen(d, s, f)
    d.rounded_rectangle([x - 8, y - 4, x + tw + 8, y + f.size + 8], 6, fill=(0, 0, 0, 120))
    d.text((x, y), s, font=f, fill=(225, 225, 225, 235))

def polaroid(img, caption, w, tilt=0.0, label_size=None):
    """white polaroid frame around img (resized to width w) with a caption; returns RGBA"""
    ih = int(w * img.height / img.width); img = img.resize((w, ih), Image.LANCZOS)
    pad = int(w * 0.06); bottom = int(w * 0.24) if caption else pad
    card = Image.new("RGBA", (w + 2 * pad, ih + pad + bottom), (246, 242, 232, 255))
    card.paste(img, (pad, pad))
    if caption:
        d = ImageDraw.Draw(card); f = fit_font(d, caption, MXB, label_size or int(w * 0.085), w)
        text_c(d, card.width / 2, ih + pad + (bottom - f.size) / 2 - 4, caption, f, (30, 30, 34))
    sh = Image.new("RGBA", (card.width + 60, card.height + 60), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([30, 38, card.width + 30, card.height + 38], fill=(0, 0, 0, 150))
    sh = sh.filter(ImageFilter.GaussianBlur(12)); sh.alpha_composite(card, (30, 30))
    return sh.rotate(tilt, Image.BICUBIC, expand=True) if tilt else sh

def paste_rgba(canvas, im, cx, cy, scale=1.0, alpha=1.0):
    if scale != 1.0: im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if alpha < 1.0:
        a = im.getchannel("A").point(lambda v: int(v * alpha)); im = im.copy(); im.putalpha(a)
    canvas.paste(im, (int(cx - im.width / 2), int(cy - im.height / 2)), im)

def red_circle(canvas, cx, cy, r, prog, width=9, col=RED):
    if prog <= 0: return
    d = ImageDraw.Draw(canvas, "RGBA")
    d.arc([cx - r, cy - r, cx + r, cy + r], -100, -100 + 360 * eout(prog), fill=col + (255,), width=width)

def arrow(canvas, x0, y0, x1, y1, prog, col=GOLD, width=10):
    if prog <= 0: return
    e = eout(prog); xe, ye = x0 + (x1 - x0) * e, y0 + (y1 - y0) * e
    d = ImageDraw.Draw(canvas, "RGBA"); d.line([(x0, y0), (xe, ye)], fill=col + (255,), width=width)
    ang = math.atan2(ye - y0, xe - x0); L = width * 3.2
    pts = [(xe, ye), (xe - L * math.cos(ang - 0.45), ye - L * math.sin(ang - 0.45)), (xe - L * math.cos(ang + 0.45), ye - L * math.sin(ang + 0.45))]
    d.polygon(pts, fill=col + (255,))

def big_label(canvas, cx, y, txt, size, hl=None):
    """'THAT'S HACHIKO' style: white words, the highlighted word yellow, heavy stroke"""
    d = ImageDraw.Draw(canvas); f = font(MB, size); words = txt.split()
    tw = tlen(d, txt, f); x = cx - tw / 2
    for i, w in enumerate(words):
        col = GOLD if (hl is not None and w.strip(".,!?").upper() == hl.upper()) or (hl is None and i == len(words) - 1) else WHITE
        d.text((x, y), w, font=f, fill=col, stroke_width=max(4, size // 11), stroke_fill=INK); x += tlen(d, w + " ", f)

# ------------------------------------------------------------------ header (9:16) + overlays
def header(canvas):
    hb = G["head"]
    if "hdr" not in _cache:
        im = panel_tex(W, hb, 21); d = ImageDraw.Draw(im)
        f = fit_font(d, CFG.HEADER_TITLE, MB, 64, W - 140)
        text_c(d, W / 2, 128, CFG.HEADER_TITLE, f, WHITE)
        f2 = fit_font(d, CFG.HEADER_SUB, MXB, 32, W - 200)
        text_c(d, W / 2, 128 + f.size + 26, CFG.HEADER_SUB, f2, GOLD, spacing=3)
        d.rectangle([0, hb - 7, W, hb], fill=RED)
        _cache["hdr"] = im
    canvas.paste(_cache["hdr"], (0, 0))

def corner_tag(canvas):   # 16:9 small series tag
    d = ImageDraw.Draw(canvas, "RGBA"); f = font(MXB, 24); txt = CFG.HEADER_SUB
    tw = tlen(d, txt, f); x = W - tw - 70 - 30
    d.rounded_rectangle([x, 28, x + tw + 70, 76], 10, fill=(10, 10, 12, 190))
    d.rectangle([x, 28, x + 10, 76], fill=RED); d.text((x + 26, 38), txt, font=f, fill=GOLD + (255,))

def hook_overlay(canvas, o, gt):
    lt = gt - o["t0"]; dur = o["t1"] - o["t0"]
    a = ease((o["t1"] - gt) / 0.25)
    if a <= 0: return
    d = ImageDraw.Draw(canvas)
    lines = o["lines"]; n = len(lines)
    maxw = W * (0.86 if FMT == "V" else 0.80)
    sizes = []
    for txt, col in lines:
        size = int(H * (0.105 if FMT == "V" else 0.13))
        f = font(MB, size)
        while tlen(d, txt, f) > maxw and size > 40: size -= 3; f = font(MB, size)
        sizes.append(size)
    lh = [s * 1.08 for s in sizes]; total = sum(lh)
    y = (H * 0.60 - total / 2) if FMT == "V" else (H * 0.58 - total / 2)
    # dark gradient behind for legibility
    ov = Image.new("RGBA", canvas.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.rectangle([0, y - 90, W, y + total + 90], fill=(0, 0, 0, int(95 * a)))
    ov = ov.filter(ImageFilter.GaussianBlur(40)); canvas.paste(ov, (0, 0), ov)
    for i, ((txt, col), size) in enumerate(zip(lines, sizes)):
        st = i * 0.16; p = back((lt - st) / 0.28) if lt >= st else 0
        if p <= 0: y += lh[i]; continue
        f = font(MB, max(8, int(size * (0.6 + 0.4 * p))))
        c = {"y": GOLD, "r": (255, 70, 60), "w": WHITE}[col]
        tw = tlen(d, txt, f); fx = (W / 2 if FMT == "V" else W / 2) - tw / 2
        layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
        ld.text((fx, y + (size - f.size) / 2), txt, font=f, fill=c + (255,), stroke_width=max(6, size // 10), stroke_fill=INK + (255,))
        if a < 1: layer.putalpha(layer.getchannel("A").point(lambda v: int(v * a)))
        canvas.paste(layer, (0, 0), layer)
        y += lh[i]

def title_overlay(canvas, o, gt):
    lt = gt - o["t0"]; a = ease(lt / 0.5) * ease((o["t1"] - gt) / 0.4)
    if a <= 0: return
    ov = Image.new("RGBA", canvas.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    cy = H * (0.60 if FMT == "V" else 0.62)
    s1 = 190 if FMT == "V" else 200
    od.rectangle([0, cy - 70, W, cy + s1 + 150], fill=(0, 0, 0, int(140 * a)))
    ov = ov.filter(ImageFilter.GaussianBlur(30)); od = ImageDraw.Draw(ov)
    sc = 0.9 + 0.1 * eout(lt / 0.6); f1 = font(PF, int(s1 * sc))
    tw = tlen(od, CFG.TITLE_BIG, f1); od.text((W / 2 - tw / 2, cy), CFG.TITLE_BIG, font=f1, fill=WHITE + (int(255 * a),))
    f2 = font(MXB, 46 if FMT == "V" else 48)
    ws = [tlen(od, c, f2) for c in CFG.TITLE_SMALL]; sp = 12; x = W / 2 - (sum(ws) + sp * (len(ws) - 1)) / 2
    for c, cw in zip(CFG.TITLE_SMALL, ws): od.text((x, cy + s1 * 1.22), c, font=f2, fill=GOLD + (int(255 * a),)); x += cw + sp
    lw = 300 * eout((lt - 0.2) / 0.8); od.rectangle([W / 2 - lw, cy + s1 * 1.22 + 74, W / 2 + lw, cy + s1 * 1.22 + 80], fill=RED + (int(255 * a),))
    canvas.paste(ov, (0, 0), ov)

def place_overlay(canvas, o, gt, box):
    a = ease((gt - o["t0"]) / 0.4) * ease((o["t1"] - gt) / 0.3)
    if a <= 0 or not box: return
    x = box[0] + 30 - (1 - a) * 50; y = box[1] + 30
    chip(canvas, x, y, o["text"], size=30 if FMT == "V" else 28, bg=(16, 16, 18), alpha=a, dot=True)

# ------------------------------------------------------------------ captions
def draw_captions(canvas, gt, zone):
    """zone = (cx, y_center, maxw) or None to hide"""
    if zone is None: return
    cx, yc, maxw = zone
    for c in TL["caps"]:
        if not (c["t0"] - 0.03 <= gt < c["t1"] + 0.15): continue
        d = ImageDraw.Draw(canvas)
        if "quote" in c:   # real audio subtitle (yellow) is drawn by the freeze panel; fallback here
            f = font(MXB, int(G["cap_size"] * 0.8)); lines = wrap(d, c["quote"].upper(), f, maxw)[:3]
            y = yc - len(lines) * f.size * 0.6
            for l in lines: text_c(d, cx, y, l, f, GOLD, stroke=6); y += f.size * 1.2
            return
        words = c["words"]; size = G["cap_size"]
        f = font(MB, size); toks = [w for w, _, _ in words]
        lines = balanced(d, [t.upper() for t in toks], f, maxw)
        while (len(lines) > 2 or any(tlen(d, " ".join(l), f) > maxw for l in lines)) and size > 36:
            size -= 4; f = font(MB, size); lines = balanced(d, [t.upper() for t in toks], f, maxw)
        pop = back((gt - c["t0"]) / 0.16); f2 = font(MB, max(8, int(size * (0.86 + 0.14 * min(1.0, pop)))))
        lh = size * 1.18; y = yc - lh * len(lines) / 2 + (size - f2.size) / 2
        wi = 0
        for l in lines:
            tw = tlen(d, " ".join(l), f2); x = cx - tw / 2
            for w in l:
                _, a, b = words[wi]
                active = (a - 0.04 <= gt < b + 0.06) or (wi == len(words) - 1 and gt >= a)
                d.text((x, y), w, font=f2, fill=GOLD if active else WHITE, stroke_width=max(6, size // 9), stroke_fill=INK)
                x += tlen(d, w + " ", f2); wi += 1
            y += lh
        return

# ------------------------------------------------------------------ layouts
class Shot:
    """renders one span; frame(lt) -> (canvas, caption_zone, media_box)"""
    def __init__(self, sp):
        self.sp = sp; self.sh = sp["shot"]; self.dur = sp["t1"] - sp["t0"]; self.srcs = []; self.hook = False
    def src(self, m, bw, bh):
        s = make_src(m, bw, bh, self.dur); self.srcs.append(s); return s
    def close(self):
        for s in self.srcs:
            if hasattr(s, "close"): s.close()
    def cap_default(self):
        return (G["cap_cx"], G["cap_y"], G["cap_w"])

def media_box_full():
    return (0, G["head"], W, H) if FMT == "V" else (0, 0, W, H)

class Full(Shot):
    def __init__(self, sp, hook=False):
        super().__init__(sp); self.hook = hook
        x0, y0, x1, y1 = (0, 0, W, H) if hook else media_box_full()
        self.box = (x0, y0, x1, y1); self.s = self.src(self.sh["media"], x1 - x0, y1 - y0)
        self.pol = {}
    def frame(self, lt, gt):
        x0, y0, x1, y1 = self.box
        can = Image.new("RGB", (W, H)); img = self.s.frame(lt, self.dur)
        if self.sh.get("punch") and lt < 0.3:
            z = 1 + 0.07 * (1 - eout(lt / 0.3)); iw, ih = img.size
            img = img.resize((iw, ih), Image.BICUBIC, box=(iw * (1 - 1 / z) / 2, ih * (1 - 1 / z) / 2, iw * (1 + 1 / z) / 2, ih * (1 + 1 / z) / 2))
        can.paste(img, (x0, y0))
        gh = int((y1 - y0) * 0.42); g = gradient(W, gh, 0.0, 0.78)
        can.paste(g, (0, y1 - gh), g)
        self.pops(can, lt, img)
        if not self.hook: credit_line(can, 40 if FMT == "V" else 40, (1652 if FMT == "V" else 1030), self.s.credit)
        return can, self.cap_default(), self.box
    def pops(self, can, lt, img):
        x0, y0, x1, y1 = self.box; bw, bh = x1 - x0, y1 - y0
        for i, p in enumerate(self.sh.get("pops", [])):
            pt = lt - p["t"]
            if pt < 0: continue
            if p["p"] == "polaroid":
                if i not in self.pol:
                    m = p["media"]; ph = CFG.PH[m["key"]]; im = tone_photo(Image.open(ph["file"]).convert("RGB"), m.get("tone"))
                    if m.get("crop"): im = im.crop(m["crop"])
                    tilt = p["tilt"] if p["tilt"] is not None else random.Random(i * 7 + len(p["caption"])).uniform(-6, 6)
                    self.pol[i] = polaroid(im, p["caption"], int(bw * (0.40 if FMT == "V" else 0.24)), tilt)
                pol = self.pol[i]; sc = back(pt / 0.35)
                pos = p["pos"]; mx = 0.70 if FMT == "V" else 0.80
                cx = x0 + bw * (mx if "r" in pos else 0.27 if FMT == "V" else 0.18)
                cy = y0 + bh * (0.30 if "t" in pos else (0.52 if FMT == "V" else 0.52))
                if FMT == "V": cx = min(cx, G["safe_r"] - pol.width / 2 + 20)
                paste_rgba(can, pol, cx, cy, max(0.05, sc))
            elif p["p"] == "stamp":
                d = ImageDraw.Draw(can, "RGBA"); sc = back(pt / 0.25); size = int((54 if FMT == "V" else 50) * max(0.1, sc))
                f = font(MB, size); tw = tlen(d, p["text"], f)
                L = Image.new("RGBA", (int(tw + 50), int(size * 1.7)), (0, 0, 0, 0)); ld = ImageDraw.Draw(L)
                ld.rounded_rectangle([0, 0, L.width - 1, L.height - 1], 12, fill=RED + (240,))
                ld.text((25, size * 0.25), p["text"], font=f, fill=WHITE)
                L = L.rotate(-3, Image.BICUBIC, expand=True)
                can.paste(L, (int(x0 + 34), int(y0 + 40)), L)
            elif p["p"] == "chip":
                col = {"yellow": (GOLD, INK), "red": (RED, WHITE), "dark": ((16, 16, 18), WHITE)}[p["color"]]
                chip(can, x0 + 34, y0 + (130 if any(q["p"] == "stamp" for q in self.sh["pops"]) else 40), p["text"], 30 if FMT == "V" else 28, bg=col[0], fg=col[1], alpha=ease(pt / 0.25))
            elif p["p"] == "pin":
                chip(can, x0 + 34, y0 + 40, p["text"], 30 if FMT == "V" else 28, bg=(16, 16, 18), alpha=ease(pt / 0.25), dot=True)
            elif p["p"] == "circle":
                cx, cy = self.s.map(p["u"], p["v"]); cx += x0; cy += y0; r = p["r"] * bw
                red_circle(can, cx, cy, r, pt / 0.45)
                if p.get("label"):
                    pa = (pt - 0.4) / 0.35
                    ly = cy + r + 150 if p["side"] == "below" else cy - r - 260
                    ly = min(ly, y1 - 360) if FMT == "V" else min(ly, y1 - 250)
                    arrow(can, cx - r * 0.2 - 120, ly - 10 if p["side"] == "below" else ly + 110, cx - r * 0.55, cy + (r * 0.75 if p["side"] == "below" else -r * 0.75), pa)
                    if pa > 0: big_label(can, min(cx, W * 0.5) if FMT == "V" else cx, ly, p["label"], 72 if FMT == "V" else 64)

class Split(Shot):
    def __init__(self, sp):
        super().__init__(sp); a, b, c, e = G["split"]
        if FMT == "V":
            self.A = (0, a, W, b); self.B = (0, c, W, e)
        else:
            self.A = (0, 0, a + 0, H); self.B = (c, 0, W, H)
            self.A = (0, 0, 1150, H); self.B = (1150, 0, W, H)
        self.sa = self.src(self.sh["top"], self.A[2] - self.A[0], self.A[3] - self.A[1])
        self.sb = self.src(self.sh["bottom"], self.B[2] - self.B[0], self.B[3] - self.B[1])
    def frame(self, lt, gt):
        can = Image.new("RGB", (W, H))
        can.paste(self.sa.frame(lt, self.dur), self.A[:2])
        bi = self.sb.frame(lt, self.dur)
        e = eout((lt - 0.15) / 0.4)
        if FMT == "V": can.paste(bi, (0, int(self.B[1] + (1 - e) * 120)))
        else: can.paste(bi, (int(self.B[0] + (1 - e) * 100), 0))
        d = ImageDraw.Draw(can, "RGBA")
        if FMT == "V":
            _, b, c, _ = G["split"]
            band = panel_tex(W, c - b, 31); can.paste(band, (0, b))
            d.rectangle([0, b, W, b + 6], fill=RED); d.rectangle([0, c - 6, W, c], fill=RED)
            zone = (G["cap_cx"], (b + c) / 2, G["cap_w"])
            credit_line(can, 30, b - 44, self.sa.credit, 20)
            credit_line(can, 30, 1650, self.sb.credit, 20)
            if self.sh.get("chip1"): chip(can, 30, self.A[1] + 28, self.sh["chip1"], 30)
            if self.sh.get("chip2"): chip(can, 30, c + 28, self.sh["chip2"], 30, bg=GOLD, fg=INK, alpha=e)
        else:
            d.rectangle([1150, 0, 1157, H], fill=RED)
            g = gradient(W, 330, 0.0, 0.8); can.paste(g, (0, H - 330), g)
            zone = (G["cap_cx"], G["cap_y"], G["cap_w"])
            credit_line(can, 30, 30 + 54 + 20, self.sa.credit, 18, right=1120)
            credit_line(can, 1180, H - 40, self.sb.credit, 18, right=1900)
            if self.sh.get("chip1"): chip(can, 30, 28 + 70 + 50, self.sh["chip1"], 28)
            if self.sh.get("chip2"): chip(can, 1180, 80, self.sh["chip2"], 28, bg=GOLD, fg=INK, alpha=e)
        return can, zone, self.A

class Board(Shot):
    """journey board: corkboard with polaroids, red string and sticky notes; camera visits each item"""
    def __init__(self, sp):
        super().__init__(sp); sh = self.sh
        y0, y1 = G["board"]; self.vy0 = y0; self.vw, self.vh = W, y1 - y0
        n = len(sh["items"]); nn = len(sh["notes"])
        BW, BH = (int(W * 1.45), int((y1 - y0) * 1.30)) if FMT == "V" else (int(W * 1.35), int(H * 1.45))
        self.board = cork(BW, BH).convert("RGBA"); d = ImageDraw.Draw(self.board)
        rng = random.Random(3); pins = []; self.focus = []
        cols = 2 if FMT == "V" else 3
        rows = (n + cols - 1) // cols
        pw = int(BW / cols * 0.66)
        for i, (m, cap) in enumerate(sh["items"]):
            r, c = divmod(i, cols)
            cx = BW * (c + 0.5) / cols + rng.uniform(-30, 30); cy = BH * (r + 0.45) / (rows + (0.6 if nn else 0)) + rng.uniform(-25, 25)
            ph = CFG.PH[m["key"]]; im = tone_photo(Image.open(ph["file"]).convert("RGB"), m.get("tone"))
            if m.get("crop"): im = im.crop(m["crop"])
            tgt = pw / (pw * 0.92)
            im = ImageOps.fit(im, (pw, int(pw * 0.86)), centering=m.get("focus", (0.5, 0.45)))
            pol = polaroid(im, cap, pw, rng.uniform(-5, 5))
            self.board.alpha_composite(pol, (int(cx - pol.width / 2), int(cy - pol.height / 2)))
            pins.append((cx, cy - pol.height / 2 + 60)); self.focus.append((cx, cy))
        ny = BH * (rows + 0.15) / (rows + 0.6) if nn else 0
        for j, (big, small) in enumerate(sh["notes"]):
            cx = BW * (j + 0.5) / max(nn, 1); cy = ny
            nw = int(pw * 0.78); note = Image.new("RGBA", (nw, int(nw * 0.82)), (255, 222, 70, 255)); nd = ImageDraw.Draw(note)
            nd.rectangle([0, 0, nw, 26], fill=(240, 205, 55, 255))
            fb = fit_font(nd, big, MB, int(nw * 0.30), nw - 50); text_c(nd, nw / 2, note.height * 0.22, big, fb, (25, 25, 25))
            fs = fit_font(nd, small, MB, int(nw * 0.12), nw - 50); text_c(nd, nw / 2, note.height * 0.66, small, fs, (190, 30, 30))
            sh_ = Image.new("RGBA", (note.width + 40, note.height + 40), (0, 0, 0, 0)); ImageDraw.Draw(sh_).rectangle([20, 28, note.width + 20, note.height + 28], fill=(0, 0, 0, 120))
            sh_ = sh_.filter(ImageFilter.GaussianBlur(8)); sh_.alpha_composite(note, (20, 20)); sh_ = sh_.rotate(rng.uniform(-6, 6), Image.BICUBIC, expand=True)
            self.board.alpha_composite(sh_, (int(cx - sh_.width / 2), int(cy - sh_.height / 2)))
            self.focus.append((cx, cy))
        for a, b in zip(pins, pins[1:]):
            d.line([a, b], fill=(170, 20, 25, 255), width=6)
        for (x, y) in pins:
            d.ellipse([x - 16, y - 16, x + 16, y + 16], fill=(200, 25, 30, 255)); d.ellipse([x - 6, y - 9, x + 2, y - 1], fill=(255, 140, 140, 255))
        self.board = self.board.convert("RGB"); self.BW, self.BH = BW, BH
        if sh.get("title"):
            d = ImageDraw.Draw(self.board); f = font(MB, 90 if FMT == "V" else 80)
    def frame(self, lt, gt):
        k = len(self.focus); pos = lt / max(self.dur, 0.1) * (k + 0.6) - 0.6
        # camera: start wide, then visit items one by one
        if pos < 0:
            cx, cy, z = self.BW / 2, self.BH / 2, max(self.vw / self.BW, self.vh / self.BH) * 1.02 + 0.0
            z = max(self.vw / self.BW, self.vh / self.BH) * (1.0 + 0.04 * (pos + 0.6))
        else:
            i = min(int(pos), k - 1); f = ease(min(1.0, (pos - i) / 0.45))
            a = self.focus[max(0, i - 1)] if i > 0 else (self.BW / 2, self.BH / 2); b = self.focus[i]
            cx, cy = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
            zw = max(self.vw / self.BW, self.vh / self.BH) * 1.0; zf = zw * (1.28 if FMT == "V" else 1.25)
            z = zw + (zf - zw) * (f if i == 0 else 1.0) if i == 0 else zf
            z = z * (1 + 0.02 * (pos - i))
        cw, ch = self.vw / z, self.vh / z
        cy += ch * 0.14 if pos >= 0 else 0      # keep the focused item above the caption zone
        x0 = min(max(0, cx - cw / 2), self.BW - cw); y0 = min(max(0, cy - ch / 2), self.BH - ch)
        view = self.board.resize((self.vw, self.vh), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
        can = Image.new("RGB", (W, H)); can.paste(view, (0, self.vy0))
        g = gradient(W, 520, 0.0, 0.70); can.paste(g, (0, H - 520), g)
        return can, self.cap_default(), (0, self.vy0, W, H)

class Freeze(Shot):
    """format 4: footage on top (left on 16:9), freezes on the key moment, red circle + arrow + label; panel with speaker,
    yellow subtitles (real audio) or captions, and a story timeline with a progress dot"""
    def __init__(self, sp):
        super().__init__(sp)
        if FMT == "V": self.box = (0, G["freeze"][0], W, G["freeze"][1])
        else: self.box = (0, 0, G["freeze"][1], H)
        x0, y0, x1, y1 = self.box; self.s = self.src(self.sh["media"], x1 - x0, y1 - y0)
        self.at = self.sh.get("at", 1.0)
    def frame(self, lt, gt):
        x0, y0, x1, y1 = self.box; frozen = lt >= self.at
        if frozen and hasattr(self.s, "frozen"): self.s.frozen = True
        img = self.s.frame(min(lt, self.at) if frozen else lt, self.dur)
        if frozen:
            f = eout((lt - self.at) / 0.5); z = 1 + 0.05 * f
            u, v = (self.sh["circle"][0], self.sh["circle"][1]) if self.sh.get("circle") else (0.5, 0.5)
            iw, ih = img.size; px, py = self.s.map(u, v)
            cw, ch = iw / z, ih / z; bx = min(max(0, px - cw / 2), iw - cw); by = min(max(0, py - ch / 2), ih - ch)
            img = img.resize((iw, ih), Image.BICUBIC, box=(bx, by, bx + cw, by + ch))
            mp = lambda uu, vv: ((self.s.map(uu, vv)[0] - bx) * z, (self.s.map(uu, vv)[1] - by) * z)
            if lt - self.at < 0.12: img = Image.blend(img, Image.new("RGB", img.size, WHITE), 0.55 * (1 - (lt - self.at) / 0.12))
        can = Image.new("RGB", (W, H)); can.paste(img, (x0, y0))
        # lower / side panel
        if FMT == "V":
            pnl = panel_tex(W, H - y1, 41); can.paste(pnl, (0, y1)); ImageDraw.Draw(can).rectangle([0, y1, W, y1 + 6], fill=RED)
        else:
            pnl = panel_tex(W - x1, H, 41); can.paste(pnl, (x1, 0)); ImageDraw.Draw(can).rectangle([x1, 0, x1 + 6, H], fill=RED)
        real = self.sp.get("sound")
        chip(can, x0 + 28, y0 + 28, "REAL VIDEO" if real else ("REAL PHOTO" if self.sh["media"]["m"] == "photo" else "REAL FOOTAGE"), 26, bg=(14, 14, 16), dot=True)
        if frozen and self.sh.get("chip"):
            d = ImageDraw.Draw(can); f = font(MXB, 26); tw = tlen(d, self.sh["chip"], f)
            chip(can, (min(x1, G["safe_r"]) if FMT == "V" else x1) - tw - 60, y0 + 28, self.sh["chip"], 26)
        if frozen and self.sh.get("circle"):
            u, v, r = self.sh["circle"]; cx, cy = mp(u, v); cx += x0; cy += y0; rr = r * (x1 - x0)
            pt = lt - self.at - 0.15
            red_circle(can, cx, cy, rr, pt / 0.45)
            if self.sh.get("label") and pt > 0.35:
                pa = (pt - 0.35) / 0.35; ly = min(y1 - 120, cy + rr + 120)
                lx = (x0 + x1) / 2
                arrow(can, lx - 160, ly - 6, cx - rr * 0.6, cy + rr * 0.7, pa)
                big_label(can, lx if FMT == "H" else min(lx, 500), ly, self.sh["label"], 70 if FMT == "V" else 60, hl=self.sh["label"].split()[-1])
        credit_line(can, x0 + 30, y1 - 44, self.s.credit, 20)
        # speaker + timeline in the panel
        d = ImageDraw.Draw(can)
        if FMT == "V":
            if self.sh.get("speaker"): text_c(d, G["cap_cx"], y1 + 40, self.sh["speaker"].upper(), font(MXB, 30), (210, 210, 210), spacing=2)
            zone = (G["cap_cx"], y1 + (1660 - y1) / 2 - 10, G["cap_w"])
            self.timeline(can, 80, G["safe_r"] - 20, 1612, gt)
        else:
            if self.sh.get("speaker"): text_c(d, (x1 + W) / 2, 120, self.sh["speaker"].upper(), font(MXB, 26), (210, 210, 210), spacing=2)
            zone = ((x1 + W) / 2, 470, W - x1 - 80)
            self.timeline(can, x1 + 50, W - 50, 900, gt)
        return can, zone, self.box
    def timeline(self, can, xa, xb, y, gt):
        T = getattr(CFG, "TIMELINE", None)
        if not T: return
        d = ImageDraw.Draw(can); d.line([(xa, y), (xb, y)], fill=(90, 90, 96), width=4)
        n = len(T); prog = self.sh.get("progress")
        if prog is None: prog = min(1.0, gt / TL["dur"])
        px = xa + (xb - xa) * prog; d.line([(xa, y), (px, y)], fill=RED, width=5)
        f = font(MXB, 22 if FMT == "V" else 18)
        for i, (lab, top) in enumerate(T):
            x = xa + (xb - xa) * i / (n - 1)
            d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=RED if x <= px + 1 else (90, 90, 96))
            text_c(d, x, y + 22, lab, f, (215, 215, 215))
            if top: text_c(d, x, y - 44, top, f, GOLD)
        d.ellipse([px - 14, y - 14, px + 14, y + 14], fill=WHITE, outline=RED, width=5)

class MapShot(Shot):
    def __init__(self, sp):
        super().__init__(sp)
        self.M = json.load(open(os.path.join(CFG.DIR, self.sh.get("file", CFG.MAPFILE))))
        y0 = G["head"] if FMT == "V" else 0; self.y0 = y0; vw, vh = W, H - y0
        mw, mh = self.M["w"], self.M["h"]
        s = max(vw / mw, vh / mh) * self.sh.get("zoom", 1.0) * 1.08; self.s = s
        BW, BH = int(mw * s), int(mh * s)
        k = ("map", FMT, id(self.M) * 0 + hash(self.sh.get("file", CFG.MAPFILE)), s)
        sea = noise_tex(BW, BH, (18, 38, 58), 12, 17)
        sd = ImageDraw.Draw(sea)
        for x in range(-BH, BW, 26): sd.line([(x, 0), (x + BH, BH)], fill=(30, 54, 78), width=2)
        for gx in range(0, BW, 104): sd.line([(gx, 0), (gx, BH)], fill=(52, 82, 112), width=3)
        for gy in range(0, BH, 104): sd.line([(0, gy), (BW, gy)], fill=(52, 82, 112), width=3)
        L = Image.new("RGBA", (BW, BH), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
        for st in self.M["states"]:
            for ring in st["rings"]:
                d.polygon([(x * s, y * s) for x, y in ring], fill=(92, 80, 60, 255), outline=(190, 168, 120, 255), width=3)
        land = noise_tex(BW, BH, (0, 0, 0), 8, 23).convert("L")
        sea = sea.convert("RGBA"); lt_ = noise_tex(BW, BH, (0, 0, 0), 14, 29).convert("L")
        La = L.getchannel("A"); tex = Image.merge("RGBA", [lt_, lt_, lt_, La.point(lambda v: 60 if v else 0)])
        sea.alpha_composite(L); sea.alpha_composite(tex)
        self.base = sea.convert("RGB"); self.BW, self.BH = BW, BH; self.vw, self.vh = vw, vh
    def tp(self, k): x, y = self.M["pts"][k]; return x * self.s, y * self.s
    def frame(self, lt, gt):
        sh = self.sh; dur = self.dur
        img = self.base.copy(); d = ImageDraw.Draw(img, "RGBA")
        fx, fy = self.tp(sh["center"]) if sh.get("center") else (self.BW / 2, self.BH / 2)
        if sh["kind"] == "route":
            pts = [self.tp(k) for k in sh["pts"]]
            prog = ease((lt - 0.5) / max(1.0, dur - 1.6))
            P = catmull(pts, 40); n = max(2, int(len(P) * prog)); seg = [tuple(p) for p in P[:n]]
            for i in range(0, len(P) - 1, 3): d.line([tuple(P[i]), tuple(P[min(i + 1, len(P) - 1)])], fill=(200, 200, 210, 120), width=4)
            d.line(seg, fill=(90, 60, 10, 255), width=16, joint="curve"); d.line(seg, fill=GOLD + (255,), width=8, joint="curve")
            hx, hy = seg[-1]; d.ellipse([hx - 15, hy - 15, hx + 15, hy + 15], fill=GOLD, outline=INK, width=4)
            cx, cy = seg[-1]
            fx = fx * 0.6 + cx * 0.4; fy = fy * 0.6 + cy * 0.4
        for k, lab, side in sh.get("towns", []):
            x, y = self.tp(k); d.ellipse([x - 11, y - 11, x + 11, y + 11], fill=RED, outline=WHITE, width=3)
            f = font(MXB, 40 if FMT == "V" else 36); tw = tlen(d, lab, f)
            tx = x + 24 if side == "r" else x - tw - 24
            d.text((tx, y - 24), lab, font=f, fill=WHITE, stroke_width=5, stroke_fill=INK)
        if sh["kind"] == "pin":
            x, y = self.tp(sh["pin"]); pr = (lt * 0.9) % 1.0; r = 22 + 90 * pr
            d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 90, 70, int(220 * (1 - pr))), width=6)
            d.ellipse([x - 17, y - 17, x + 17, y + 17], fill=RED, outline=WHITE, width=5)
        z = 1.0 + 0.06 * ease(lt / dur)
        cw, ch = self.vw / z, self.vh / z
        x0 = min(max(0, fx - cw / 2), self.BW - cw); y0 = min(max(0, fy - ch / 2), self.BH - ch)
        view = img.resize((self.vw, self.vh), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
        can = Image.new("RGB", (W, H)); can.paste(view, (0, self.y0))
        dd = ImageDraw.Draw(can)
        if sh.get("label"):
            chip(can, 34, self.y0 + 34, sh["label"], 32 if FMT == "V" else 30, bg=(14, 14, 16))
        if sh.get("counter"):
            val, unit = sh["counter"]; v = int(val * ease((lt - 0.5) / max(1.0, dur - 1.6)))
            f = font(MB, 120 if FMT == "V" else 110)
            yy = self.y0 + (800 if FMT == "V" else 640)
            xx = G["cap_cx"] if FMT == "V" else 1560
            text_c(dd, xx, yy, f"{v:,}", f, GOLD, stroke=8)
            text_c(dd, xx, yy + f.size * 1.08, unit, font(MB, 46 if FMT == "V" else 42), WHITE, stroke=5, spacing=2)
        if sh.get("note"): text_c(dd, G["cap_cx"] if FMT == "V" else 1560, self.y0 + (1080 if FMT == "V" else 860), sh["note"], font(MM, 26), (220, 220, 220), stroke=3)
        g = gradient(W, 480, 0.0, 0.6); can.paste(g, (0, H - 480), g)
        return can, self.cap_default(), (0, self.y0, W, H)

def catmull(pts, n=40):
    out = []; P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = map(np.array, P[i - 1:i + 3])
        for k in range(n):
            s = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * s + (2 * p0 - 5 * p1 + 4 * p2 - p3) * s * s + (-p0 + 3 * p1 - 3 * p2 + p3) * s ** 3))
    out.append(np.array(pts[-1])); return out

class BgCard(Shot):
    """chapter / stat / cta: real photo behind at ~45% brightness, grain, slow zoom; text fills the card"""
    def __init__(self, sp):
        super().__init__(sp); y0 = G["head"] if FMT == "V" else 0; self.y0 = y0
        bg = self.sh.get("bg") or {"m": "photo", "key": CFG.DEFAULT_BG, "focus": (0.5, 0.45), "z": (1.0, 1.06)}
        bg = dict(bg); bg["z"] = (1.0, 1.06)
        self.s = self.src(bg, W, H - y0)
    def frame(self, lt, gt):
        img = self.s.frame(lt, self.dur)
        img = ImageEnhance.Brightness(img).enhance(0.46)
        can = Image.new("RGB", (W, H)); can.paste(img, (0, self.y0))
        can = Image.blend(can, ImageChops.overlay(can, grain_layer(int(lt * 12)).convert("RGB")), 0.35)
        d = ImageDraw.Draw(can, "RGBA"); sh = self.sh; L = sh["L"]
        cy = self.y0 + (H - self.y0) * (0.40 if FMT == "V" else 0.42)
        if L == "chapter":
            a = ease(lt / 0.45) * ease((self.dur - lt) / 0.35); rise = (1 - eout(lt / 0.7)) * 50
            ov = Image.new("RGBA", can.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
            f1 = font(MXB, 50 if FMT == "V" else 46)
            txt = f"CHAPTER {sh['n']}"; ws = [tlen(od, c, f1) for c in txt]; sp = 16; x = W / 2 - (sum(ws) + sp * (len(ws) - 1)) / 2
            for c, cw in zip(txt, ws): od.text((x, cy - 150 + rise), c, font=f1, fill=GOLD + (int(255 * a),)); x += cw + sp
            f2 = font(PF, 150 if FMT == "V" else 150); lines = wrap(od, sh["title"], f2, W * 0.86)
            while len(lines) > 2: f2 = font(PF, f2.size - 10); lines = wrap(od, sh["title"], f2, W * 0.86)
            for i, l in enumerate(lines):
                tw = tlen(od, l, f2); od.text((W / 2 - tw / 2, cy - 40 + i * f2.size * 1.1 + rise), l, font=f2, fill=WHITE + (int(255 * a),), stroke_width=2, stroke_fill=(0, 0, 0, int(160 * a)))
            lw = 280 * eout((lt - 0.2) / 0.8); yl = cy - 10 + len(lines) * f2.size * 1.1 + 30 + rise
            od.rectangle([W / 2 - lw, yl, W / 2 + lw, yl + 7], fill=RED + (int(255 * a),))
            can.paste(ov, (0, 0), ov)
            return can, None, None
        if L == "stat":
            big = sh["big"]
            if re.fullmatch(r"~?[\d,]+\+?", big):
                num = int(re.sub(r"\D", "", big)); v = int(num * eout(lt / 1.5))
                s = ("~" if big.startswith("~") else "") + f"{v:,}" + ("+" if big.endswith("+") else "")
            else: s = big
            f = font(MB, 340 if FMT == "V" else 300)
            while tlen(d, big, f) > W * 0.84: f = font(MB, f.size - 10)
            sc = back(lt / 0.4)
            ff = font(MB, max(10, int(f.size * (0.7 + 0.3 * min(1.0, sc)))))
            text_c(d, W / 2, cy - ff.size * 0.55, s, ff, GOLD, stroke=10)
            fs = fit_font(d, sh["small"], MB, 66 if FMT == "V" else 62, W * 0.86)
            ls = wrap(d, sh["small"], fs, W * 0.86)
            for i, l in enumerate(ls): text_c(d, W / 2, cy + f.size * 0.62 + i * fs.size * 1.2, l, fs, WHITE, stroke=6, spacing=2)
            if sh.get("sub"): text_c(d, W / 2, cy + f.size * 0.62 + len(ls) * fs.size * 1.2 + 20, sh["sub"], font(MSB, 34), (225, 225, 225), stroke=3)
            return can, self.cap_default(), None
        if L == "cta":
            if sh["k"] == 0:
                sc = 1 + 0.05 * math.sin(lt * 4.5) * ease((lt - 0.6) / 0.3); bw, bh = 660 * sc, 160 * sc
                text_c(d, W / 2, cy - 330, "MORE TRUE STORIES OF", font(MB, 60 if FMT == "V" else 58), WHITE, stroke=5)
                text_c(d, W / 2, cy - 250, "INCREDIBLE DOGS", font(MB, 92 if FMT == "V" else 84), GOLD, stroke=6)
                d.rounded_rectangle([W / 2 - bw / 2, cy - bh / 2, W / 2 + bw / 2, cy + bh / 2], int(bh / 2), fill=(225, 30, 40))
                text_c(d, W / 2, cy - 48 * sc, "SUBSCRIBE", font(MB, int(84 * sc)), WHITE)
                text_c(d, W / 2, cy + 150, "🔔" if False else "AND TAP THE BELL", font(MXB, 46), WHITE, stroke=4, spacing=3)
            else:
                bw = W * (0.86 if FMT == "V" else 0.66); f = font(MXB, 66 if FMT == "V" else 62)
                lines = wrap(d, CFG.CTA_Q, f, bw - 110); bh = len(lines) * f.size * 1.25 + 120
                x0 = W / 2 - bw / 2; y0 = cy - bh / 2 - 60
                pop = back(lt / 0.4);
                d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], 44, fill=(250, 250, 250))
                d.polygon([(x0 + 130, y0 + bh - 2), (x0 + 115, y0 + bh + 80), (x0 + 230, y0 + bh - 2)], fill=(250, 250, 250))
                for i, l in enumerate(lines): text_c(d, W / 2, y0 + 60 + i * f.size * 1.25, l, f, (20, 20, 20))
                text_c(d, W / 2, y0 + bh + 130, "TELL US IN THE COMMENTS", font(MB, 54 if FMT == "V" else 52), GOLD, stroke=5, spacing=2)
            return can, None, None

def make_shot(sp, hook=False):
    L = sp["shot"]["L"]
    if L == "full": return Full(sp, hook)
    if L == "split": return Split(sp)
    if L == "board": return Board(sp)
    if L == "freeze": return Freeze(sp)
    if L == "map": return MapShot(sp)
    return BgCard(sp)

# ------------------------------------------------------------------ frame assembly
def compose(shot, lt, gt):
    can, zone, box = shot.frame(lt, gt)
    hook = [o for o in TL["overlays"] if o["kind"] == "hook" and o["t0"] <= gt < o["t1"]]
    in_hook = gt < TL.get("hook_end", 0)
    if FMT == "V" and not shot.hook: header(can)
    if FMT == "H" and not in_hook and shot.sh["L"] not in ("chapter", "cta"): corner_tag(can)
    for o in TL["overlays"]:
        if not (o["t0"] <= gt < o["t1"]): continue
        if o["kind"] == "place": place_overlay(can, o, gt, box)
        if o["kind"] == "title": title_overlay(can, o, gt)
    for o in hook: hook_overlay(can, o, gt)
    title_on = any(o["kind"] == "title" and o["t0"] + 0.3 <= gt < o["t1"] for o in TL["overlays"])
    if not hook and not title_on: draw_captions(can, gt, zone)
    return can

def render_span(idx, prev_frame=None, stills=None):
    spans = TL["spans"]; sp = spans[idx]
    f0, f1 = round(sp["t0"] * FPS), round(sp["t1"] * FPS); n = f1 - f0
    hook = sp["t0"] < TL.get("hook_end", 0) and sp["shot"]["L"] == "full"
    shot = make_shot(sp, hook); out = os.path.join(CFG.WORK, f"out_{FMT}")
    enc = None
    if stills is None:
        tmp = os.path.join(out, f"s{idx:03d}.tmp.mp4")
        enc = subprocess.Popen([FF, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
                               + video_encoder() + ["-g", "60", "-r", str(FPS), tmp], stdin=subprocess.PIPE)
    xf = 0.0 if sp.get("chapter") or idx == 0 else 0.3
    last = None; got = []
    for k in range(n):
        lt = k / FPS; gt = (f0 + k) / FPS
        if stills is not None:
            want = [s for s in stills if s != "last" and abs(gt - s) < 0.5 / FPS] or (k == n - 1 and "last" in stills)
            if not want:
                if any(isinstance(s, VideoSrc) for s in shot.srcs): shot.frame(lt, gt)   # keep video readers in sync
                continue
        can = compose(shot, lt, gt)
        if prev_frame is not None and lt < xf: can = Image.blend(prev_frame, can, ease(lt / xf))
        last = can
        if enc: enc.stdin.write(can.tobytes())
        else: got.append((gt, can))
    shot.close()
    if enc:
        enc.stdin.close(); enc.wait()
        if enc.returncode != 0: raise SystemExit(f"encode failed span {idx}")
        os.replace(tmp, os.path.join(out, f"s{idx:03d}.mp4"))
    return last, got

def last_frame_of(idx):
    _, got = render_span(idx, None, stills=["last"]); return got[-1][1] if got else None

def worker(args):
    code, fmt, idx = args
    if CFG is None or FMT != fmt: setup(code, fmt)
    prev = last_frame_of(idx - 1) if idx > 0 else None
    render_span(idx, prev)
    return idx

if __name__ == "__main__":
    code, fmt = sys.argv[1], sys.argv[2].upper()
    setup(code, fmt)
    out = os.path.join(CFG.WORK, f"out_{fmt}"); os.makedirs(out, exist_ok=True)
    spans = TL["spans"]
    if os.environ.get("STILLS"):
        ts = [float(x) for x in os.environ["STILLS"].split(",")]
        for i, sp in enumerate(spans):
            if any(sp["t0"] <= t < sp["t1"] for t in ts):
                _, got = render_span(i, None, stills=ts)
                for gt, im in got: im.save(os.path.join(out, f"still_{gt:07.2f}.jpg"), quality=88)
        print("stills written to", out); sys.exit()
    todo = list(range(len(spans)))
    if os.environ.get("PREVIEW"): todo = [i for i in todo if spans[i]["t0"] < float(os.environ["PREVIEW"])]
    if os.environ.get("ONLY"): todo = [int(x) for x in os.environ["ONLY"].split(",")]
    if os.environ.get("RESUME"): todo = [i for i in todo if not os.path.exists(os.path.join(out, f"s{i:03d}.mp4"))]
    jobs = int(os.environ.get("JOBS", max(1, (os.cpu_count() or 2) - 1)))
    print(f"[{fmt}] rendering {len(todo)} spans with {jobs} workers", flush=True)
    import multiprocessing as mp
    if jobs <= 1:
        for i in todo: worker((code, fmt, i)); print(f"[{fmt}] span {i} done", flush=True)
    else:
        with mp.get_context("spawn").Pool(jobs) as pool:
            for i in pool.imap_unordered(worker, [(code, fmt, i) for i in sorted(todo, key=lambda i: -(spans[i]["t1"] - spans[i]["t0"]))]):
                print(f"[{fmt}] span {i} done", flush=True)
