import json, math, os, subprocess, sys, re
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops
sys.path.insert(0, ".")
from cfg import SRC, PHOTOS
import cfg
import script as SCR

FMT = sys.argv[1]                      # V or H
ONLY = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 and sys.argv[2] != "all" else None
STILL_T = [float(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else None   # preview frames at global times
FPS = 30
W, H = (1080, 1920) if FMT == "V" else (1920, 1080)
OUT = f"out_{FMT}"; os.makedirs(OUT, exist_ok=True)
FD = "/home/claude/work/fonts/"
def font(name, size, _c={}):
    k = (name, size)
    if k not in _c: _c[k] = ImageFont.truetype(FD + name, size)
    return _c[k]
MB, MXB, MSB, MM = "Montserrat_900Black.ttf", "Montserrat_800ExtraBold.ttf", "Montserrat_600SemiBold.ttf", "Montserrat_500Medium.ttf"
PF = "PlayfairDisplay_900Black.ttf"
GOLD = (255, 205, 80); WHITE = (255, 255, 255)

if FMT == "V":
    WIN_MAX = (1000, 860); WIN_C = (540, 830)
    CAP_Y = 1470; CAP_SIZE = 78; CAP_MAXW = 960
    CRED_SIZE = 26; HEADER = True
else:
    WIN_MAX = (1290, 740); WIN_C = (960, 448)
    CAP_Y = 965; CAP_SIZE = 64; CAP_MAXW = 1600
    CRED_SIZE = 22; HEADER = False

tl = json.load(open("timeline.json"))
CAPS, OVER = tl["caps"], tl["overlays"] + [dict(kind="hook", t0=0.5, t1=10.4)]

def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

# ------------------------------------------------------------------ source frame readers
def cropdetect(src, t0, dur):
    r = subprocess.run(["ffmpeg", "-ss", str(t0), "-t", str(max(0.6, min(dur, 4))), "-i", src, "-vf", "cropdetect=limit=28:round=2:reset=0",
                        "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    m = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", r)
    return tuple(map(int, m[-1])) if m else None

def probe(src):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height", "-of", "csv=p=0", src],
                       capture_output=True, text=True).stdout.strip().split(",")
    return int(r[0]), int(r[1])

def fit(w, h, box):
    s = min(box[0] / w, box[1] / h); return int(round(w * s / 2) * 2), int(round(h * s / 2) * 2)

class VideoReader:
    def __init__(self, src, t_in, t_out, crop):
        sw, sh = probe(src)
        cd = cropdetect(src, t_in, t_out - t_in)
        x, y, cw, ch = (0, 0, sw, sh) if not cd else (cd[2], cd[3], cd[0], cd[1])
        if cw < sw * 0.3 or ch < sh * 0.3: x, y, cw, ch = 0, 0, sw, sh
        if isinstance(crop, dict):
            if "x0" in crop and crop["x0"] > x: cw -= crop["x0"] - x; x = crop["x0"]
            if "y0" in crop and crop["y0"] > y: ch -= crop["y0"] - y; y = crop["y0"]
            if "x1" in crop: cw = min(cw, crop["x1"] - x)
            if "ymax" in crop: ch = min(ch, crop["ymax"] - y)
            cw -= cw % 2; ch -= ch % 2
        self.w, self.h = fit(cw, ch, WIN_MAX)
        self.p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", str(t_in), "-t", str(t_out - t_in), "-i", src,
            "-vf", f"crop={cw}:{ch}:{x}:{y},scale={self.w}:{self.h}:flags=lanczos,fps={FPS}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            stdout=subprocess.PIPE)
        self.last = None; self.n = 0
    def next(self):
        b = self.p.stdout.read(self.w * self.h * 3)
        if len(b) == self.w * self.h * 3:
            self.last = Image.frombytes("RGB", (self.w, self.h), b); self.n += 1
        return self.last, (len(b) != self.w * self.h * 3)

# ------------------------------------------------------------------ drawing helpers
def rounded_mask(w, h, r):
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=255); return m
_shadow = {}
def frame_window(canvas, img, cx, cy, credit, alpha=1.0):
    w, h = img.size; x0, y0 = cx - w // 2, cy - h // 2
    key = (w, h)
    if key not in _shadow:
        sh = Image.new("L", (w + 80, h + 80), 0); ImageDraw.Draw(sh).rounded_rectangle([40, 48, w + 40, h + 48], 22, fill=170)
        _shadow[key] = (sh.filter(ImageFilter.GaussianBlur(18)), rounded_mask(w, h, 20), rounded_mask(w + 8, h + 8, 24))
    sh, m, mb = _shadow[key]
    canvas.paste((0, 0, 0), (x0 - 40, y0 - 40), sh)
    canvas.paste((245, 240, 228), (x0 - 4, y0 - 4), mb)
    canvas.paste(img, (x0, y0), m)
    if credit:
        f = font(MM, CRED_SIZE); txt = "Source: " + credit
        d = ImageDraw.Draw(canvas); tw = d.textlength(txt, font=f)
        if tw > W - 60:
            f = font(MM, int(CRED_SIZE * (W - 60) / tw)); tw = d.textlength(txt, font=f)
        d.text((cx - tw / 2, y0 + h + 22), txt, font=f, fill=(215, 215, 215))
    return (x0, y0, w, h)

def blur_bg(img, dark=0.42):
    small = img.resize((max(8, img.width // 14), max(8, img.height // 14)), Image.BILINEAR).filter(ImageFilter.GaussianBlur(1.4))
    sw, sh = small.size; s = max(W / sw, H / sh)
    big = small.resize((int(sw * s) + 2, int(sh * s) + 2), Image.BILINEAR)
    big = big.crop(((big.width - W) // 2, (big.height - H) // 2, (big.width - W) // 2 + W, (big.height - H) // 2 + H))
    return Image.blend(Image.new("RGB", (W, H), (8, 8, 10)), big, dark)

_vig = None
def vignette():
    global _vig
    if _vig is None:
        y, x = np.mgrid[0:H, 0:W]; r = np.sqrt(((x - W / 2) / (W / 1.3)) ** 2 + ((y - H / 2) / (H / 1.3)) ** 2)
        a = np.clip(1 - 0.55 * r ** 2, 0.25, 1)
        base = np.zeros((H, W, 3)); base[..., 0] = 36; base[..., 1] = 26; base[..., 2] = 18
        _vig = Image.fromarray((base * a[..., None] + 6).astype(np.uint8))
    return _vig.copy()

def zoom(img, z, size=None, pan=(0.5, 0.5)):
    w, h = img.size; cw, ch = w / z, h / z
    x0 = (w - cw) * pan[0]; y0 = (h - ch) * pan[1]
    return img.resize(size or (w, h), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))

def text_center(d, y, txt, f, fill, stroke=0, sfill=(0, 0, 0), spacing=0, x=None):
    if spacing:
        widths = [d.textlength(c, font=f) for c in txt]; tw = sum(widths) + spacing * (len(txt) - 1)
        xx = (x if x is not None else W / 2) - tw / 2
        for c, cw in zip(txt, widths):
            d.text((xx, y), c, font=f, fill=fill, stroke_width=stroke, stroke_fill=sfill); xx += cw + spacing
        return
    tw = d.textlength(txt, font=f); d.text(((x if x is not None else W / 2) - tw / 2, y), txt, font=f, fill=fill, stroke_width=stroke, stroke_fill=sfill)

# ------------------------------------------------------------------ captions & overlays (global time)
def draw_captions(canvas, t):
    if any(o["kind"] == "title" and o["t0"] + 0.3 <= t < o["t1"] for o in OVER): return
    d = ImageDraw.Draw(canvas)
    for c in CAPS:
        if c["t0"] - 0.02 <= t < c["t1"] + 0.12:
            if "quote" in c:
                f = font(MSB, int(CAP_SIZE * 0.66)); fs = font(MXB, int(CAP_SIZE * 0.38))
                lines = wrap(d, c["quote"], f, CAP_MAXW - 80)
                lh = int(CAP_SIZE * 0.82); bh = lh * len(lines) + 90; y0 = CAP_Y - 50
                bw = max(d.textlength(l, font=f) for l in lines) + 80
                ov = Image.new("RGBA", canvas.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
                od.rounded_rectangle([W / 2 - bw / 2, y0, W / 2 + bw / 2, y0 + bh], 18, fill=(0, 0, 0, 165))
                canvas.paste(ov, (0, 0), ov)
                text_center(d, y0 + 16, c["speaker"].upper(), fs, GOLD)
                for i, l in enumerate(lines): text_center(d, y0 + 62 + i * lh, l, f, WHITE)
            else:
                f = font(MB, CAP_SIZE)
                words = c["words"]; txt = " ".join(w for w, _, _ in words).upper()
                lines = wrap(d, txt, f, CAP_MAXW)
                pop = 0.92 + 0.08 * ease((t - c["t0"]) / 0.12)
                ff = font(MB, int(CAP_SIZE * pop))
                y = CAP_Y + (1 - pop) * CAP_SIZE / 2 - (len(lines) - 1) * CAP_SIZE * 0.6
                wi = 0
                for l in lines:
                    lw = l.split(); tw = d.textlength(l, font=ff); x = W / 2 - tw / 2
                    for w_ in lw:
                        _, a, b = words[wi]; active = a - 0.03 <= t < b + 0.05 or (wi == len(words) - 1 and t >= a)
                        d.text((x, y), w_, font=ff, fill=GOLD if active else WHITE, stroke_width=7, stroke_fill=(0, 0, 0))
                        x += d.textlength(w_ + " ", font=ff); wi += 1
                    y += CAP_SIZE * 1.2
            break

def wrap(d, txt, f, maxw):
    out, cur = [], ""
    for w_ in txt.split():
        test = (cur + " " + w_).strip()
        if d.textlength(test, font=f) <= maxw or not cur: cur = test
        else: out.append(cur); cur = w_
    if cur: out.append(cur)
    return out

def draw_overlays(canvas, t, win):
    d = ImageDraw.Draw(canvas)
    hook_on = any(o["kind"] == "hook" and o["t0"] <= t < o["t1"] for o in OVER)
    if HEADER and not hook_on:
        text_center(d, 178, "TRUE STORY", font(MXB, 26), GOLD, spacing=8)
        text_center(d, 216, cfg.HEADER, font(MXB, 34), (235, 235, 235), spacing=3)
    for o in OVER:
        if not (o["t0"] <= t < o["t1"]): continue
        a = ease((t - o["t0"]) / 0.45) * ease((o["t1"] - t) / 0.35)
        if o["kind"] == "place" and win:
            f = font(MXB, 30 if FMT == "V" else 28); tw = d.textlength(o["text"], font=f) + 44
            x0, y0 = win[0] + 26 - (1 - a) * 40, win[1] + 26
            ov = Image.new("RGBA", canvas.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
            od.rounded_rectangle([x0, y0, x0 + tw, y0 + 56], 28, fill=(15, 15, 15, int(205 * a)))
            od.ellipse([x0 + 16, y0 + 22, x0 + 28, y0 + 34], fill=(230, 70, 60, int(255 * a)))
            od.text((x0 + 38, y0 + 12), o["text"], font=f, fill=(255, 255, 255, int(255 * a)))
            canvas.paste(ov, (0, 0), ov)
        if o["kind"] == "hook":
            lt = t - o["t0"]; a = ease((o["t1"] - t) / 0.4); pop = 1.0 if lt > 0.25 else 0.85 + 0.15 * ease(lt / 0.25)
            ov = Image.new("RGBA", canvas.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
            if FMT == "V":
                f1 = font(MB, int(70 * pop)); f2 = font(MB, int(92 * pop)); y1 = 120
                for txt, f, col, y in [(cfg.HOOK_V[0], f1, (255, 255, 255), y1), (cfg.HOOK_V[1], f1, (255, 255, 255), y1 + 82), (cfg.HOOK_V[2], f2, GOLD, y1 + 170)]:
                    tw = od.textlength(txt, font=f)
                    if tw > W - 70: f = font(MB, int(f.size * (W - 70) / tw)); tw = od.textlength(txt, font=f)
                    od.text((W / 2 - tw / 2, y), txt, font=f, fill=col + (int(255 * a),), stroke_width=7, stroke_fill=(0, 0, 0, int(255 * a)))
            else:
                f1 = font(MB, int(52 * pop)); txt1, txt2 = cfg.HOOK_H
                w1 = od.textlength(txt1, font=f1); w2 = od.textlength(txt2, font=f1)
                if w1 + w2 > W - 60: f1 = font(MB, int(f1.size * (W - 60) / (w1 + w2))); w1 = od.textlength(txt1, font=f1); w2 = od.textlength(txt2, font=f1)
                x = W / 2 - (w1 + w2) / 2
                od.rectangle([0, 0, W, 92], fill=(0, 0, 0, int(140 * a)))
                od.text((x, 18), txt1, font=f1, fill=(255, 255, 255, int(255 * a)), stroke_width=5, stroke_fill=(0, 0, 0, int(255 * a)))
                od.text((x + w1, 18), txt2, font=f1, fill=GOLD + (int(255 * a),), stroke_width=5, stroke_fill=(0, 0, 0, int(255 * a)))
            canvas.paste(ov, (0, 0), ov)
        if o["kind"] == "title":
            ov = Image.new("RGBA", canvas.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
            s1, s2 = (150, 64) if FMT == "V" else (150, 60)
            yb = (win[1] + win[3] - 330) if (FMT == "H" and win) else 1270
            od.rectangle([0, yb - 30, W, yb + s1 + s2 + 90], fill=(0, 0, 0, int(150 * a)))
            sc = 0.9 + 0.1 * ease((t - o["t0"]) / 0.6)
            f1 = font(PF, int(s1 * sc)); f2 = font(MXB, int(s2 * 0.62))
            tw = od.textlength(cfg.TITLE_BIG, font=f1)
            od.text((W / 2 - tw / 2, yb), cfg.TITLE_BIG, font=f1, fill=(255, 255, 255, int(255 * a)))
            txt = cfg.TITLE_SMALL; widths = [od.textlength(c, font=f2) for c in txt]; sp = 12
            xx = W / 2 - (sum(widths) + sp * (len(txt) - 1)) / 2
            for c, cw in zip(txt, widths):
                od.text((xx, yb + s1 * 1.12), c, font=f2, fill=GOLD + (int(255 * a),)); xx += cw + sp
            canvas.paste(ov, (0, 0), ov)

# ------------------------------------------------------------------ special scenes
MAP = json.load(open(cfg.MAPFILE))
def map_layer(scale, ox, oy):
    key = (scale, ox, oy)
    if not hasattr(map_layer, "c"): map_layer.c = {}
    if key in map_layer.c: return map_layer.c[key]
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for st in MAP["states"]:
        for ring in st["rings"]:
            pts = [(ox + x * scale, oy + y * scale) for x, y in ring]
            hl = st["name"] in getattr(cfg, "HILITE", ())
            d.polygon(pts, fill=(58, 48, 36, 255) if hl else (34, 38, 46, 255), outline=(92, 104, 122, 255))
    map_layer.c[key] = im; return im

def catmull(pts, n=40):
    out = []
    P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = map(np.array, P[i - 1:i + 3])
        for k in range(n):
            s = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * s + (2 * p0 - 5 * p1 + 4 * p2 - p3) * s * s + (-p0 + 3 * p1 - 3 * p2 + p3) * s ** 3))
    out.append(np.array(pts[-1])); return out

def render_map(kind, lt, dur):
    can = vignette()
    scale = (1000 / 975) if FMT == "V" else (1120 / 975)
    mw, mh = 975 * scale, 610 * scale
    ox, oy = (W - mw) / 2, (WIN_C[1] - mh / 2) if FMT == "V" else 100
    can.paste(map_layer(scale, ox, oy), (0, 0), map_layer(scale, ox, oy))
    d = ImageDraw.Draw(can)
    P = MAP["pts"]; tp = lambda k: (ox + P[k][0] * scale, oy + P[k][1] * scale)
    if kind == "MAP_PIN":
        name, lab, toplab = cfg.PIN
        x, y = tp(name); pr = (lt * 1.2) % 1.0
        for rr, al in [(18 + 60 * pr, int(200 * (1 - pr)))]:
            ov = Image.new("RGBA", can.size, (0, 0, 0, 0)); ImageDraw.Draw(ov).ellipse([x - rr, y - rr, x + rr, y + rr], outline=(255, 90, 70, al), width=5); can.paste(ov, (0, 0), ov)
        d.ellipse([x - 13, y - 13, x + 13, y + 13], fill=(230, 70, 60), outline=WHITE, width=4)
        f = font(MXB, 34); tw = d.textlength(lab, font=f)
        lx = x - tw - 26 if x - tw - 26 > 20 else x + 26
        d.text((lx, y - 20), lab, font=f, fill=WHITE, stroke_width=5, stroke_fill=(0, 0, 0))
        for nm, lb in getattr(cfg, "PIN_EXTRA", []):
            x2, y2 = tp(nm); d.ellipse([x2 - 6, y2 - 6, x2 + 6, y2 + 6], fill=(200, 200, 200))
            d.text((x2 + 12, y2 - 14), lb, font=font(MSB, 24), fill=(210, 210, 210), stroke_width=3, stroke_fill=(0, 0, 0))
        yl = (oy - 120) if FMT == "V" else 32
        text_center(d, yl, toplab, font(MXB, 40 if FMT == "V" else 44), GOLD, spacing=2)
        return can, None
    if kind == "MAP_ROUTE":
        R = cfg.ROUTES[cfg._route_key]
        full = [tp(n) for n in cfg.RELAY]
        for i in range(len(full) - 1): d.line([full[i], full[i + 1]], fill=(110, 110, 120), width=4)
        path = catmull([tp(n) for n in R["pts"]], 30)
        prog = ease((lt - 0.4) / max(1.0, dur - 1.4)); nn = max(2, int(len(path) * prog))
        seg = [tuple(p) for p in path[:nn]]
        d.line(seg, fill=(120, 90, 30), width=14, joint="curve"); d.line(seg, fill=R["color"], width=7, joint="curve")
        hx, hy = seg[-1]; d.ellipse([hx - 12, hy - 12, hx + 12, hy + 12], fill=R["color"], outline=(0, 0, 0), width=3)
        for n, lab, side in cfg.TOWNS:
            x, y = tp(n); d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(230, 70, 60), outline=WHITE, width=2)
            f = font(MXB, 26 if FMT == "V" else 28); tw = d.textlength(lab, font=f)
            tx = x + 14 if side == "r" else x - tw - 14; ty = y - 40 if side != "b" else y + 12
            if side in ("b", "t"): tx = x - tw / 2
            if side == "r": ty = y - 16
            d.text((tx, ty), lab, font=f, fill=WHITE, stroke_width=4, stroke_fill=(0, 0, 0))
        yl = (oy - 120) if FMT == "V" else 32
        text_center(d, yl, R["label"], font(MXB, 40 if FMT == "V" else 44), GOLD, spacing=2)
        if R.get("miles"):
            mi = int(R["miles"] * prog)
            text_center(d, oy + mh + (40 if FMT == "V" else -10), f"{mi:,} MILES", font(MB, 96 if FMT == "V" else 72), WHITE, stroke=6,
                        x=None if FMT == "V" else ox + mw - 230)
        return can, None
    if kind == "MAP_OUT":
        route = [tp("Silverton"), tp("Boise"), tp("SaltLake"), tp("Cheyenne"), tp("Omaha"), tp("DesMoines"), tp("Wolcott")]
        col = (200, 200, 210); label = "AUGUST 1923 · THE FAMILY DRIVES EAST"
    else:
        route = [tp("Wolcott"), tp("DesMoines"), tp("Omaha"), tp("Cheyenne"), tp("ContinentalDivide"), tp("Boise"), tp("Silverton")]
        col = GOLD; label = "1923–1924 · BOBBIE WALKS HOME"
    path = catmull(route)
    prog = ease((lt - 0.4) / (dur - 1.6))
    n = max(2, int(len(path) * prog))
    seg = [tuple(p) for p in path[:n]]
    if kind == "MAP_ROUTE":
        R = cfg.ROUTES[cfg._route_key]
        full = [tp(n) for n in cfg.RELAY]
        for i in range(len(full) - 1): d.line([full[i], full[i + 1]], fill=(110, 110, 120), width=4)
        path = catmull([tp(n) for n in R["pts"]], 30)
        prog = ease((lt - 0.4) / max(1.0, dur - 1.4)); nn = max(2, int(len(path) * prog))
        seg = [tuple(p) for p in path[:nn]]
        d.line(seg, fill=(120, 90, 30), width=14, joint="curve"); d.line(seg, fill=R["color"], width=7, joint="curve")
        hx, hy = seg[-1]; d.ellipse([hx - 12, hy - 12, hx + 12, hy + 12], fill=R["color"], outline=(0, 0, 0), width=3)
        for n, lab, side in cfg.TOWNS:
            x, y = tp(n); d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(230, 70, 60), outline=WHITE, width=2)
            f = font(MXB, 26 if FMT == "V" else 28); tw = d.textlength(lab, font=f)
            tx = x + 14 if side == "r" else x - tw - 14; ty = y - 40 if side != "b" else y + 12
            if side in ("b", "t"): tx = x - tw / 2
            if side == "r": ty = y - 16
            d.text((tx, ty), lab, font=f, fill=WHITE, stroke_width=4, stroke_fill=(0, 0, 0))
        yl = (oy - 120) if FMT == "V" else 32
        text_center(d, yl, R["label"], font(MXB, 40 if FMT == "V" else 44), GOLD, spacing=2)
        if R.get("miles"):
            mi = int(R["miles"] * prog)
            text_center(d, oy + mh + (40 if FMT == "V" else -10), f"{mi:,} MILES", font(MB, 96 if FMT == "V" else 72), WHITE, stroke=6,
                        x=None if FMT == "V" else ox + mw - 230)
        return can, None
    if kind == "MAP_OUT":
        for i in range(0, len(seg) - 1, 2): d.line([seg[i], seg[i + 1]], fill=col, width=6)
    else:
        d.line(seg, fill=(120, 90, 30), width=14, joint="curve"); d.line(seg, fill=col, width=7, joint="curve")
    hx, hy = seg[-1]; d.ellipse([hx - 13, hy - 13, hx + 13, hy + 13], fill=col, outline=(0, 0, 0), width=3)
    for name, lab, dx in [("Silverton", "SILVERTON, OR", 1), ("Wolcott", "WOLCOTT, IN", -1)]:
        x, y = tp(name); d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=(230, 70, 60), outline=WHITE, width=3)
        f = font(MXB, 30 if FMT == "V" else 32); tw = d.textlength(lab, font=f)
        tx = x + 18 if dx > 0 else x - tw - 18
        d.text((tx, y - 46), lab, font=f, fill=WHITE, stroke_width=4, stroke_fill=(0, 0, 0))
    yl = (oy - 120) if FMT == "V" else 32
    text_center(d, yl, label, font(MXB, 40 if FMT == "V" else 44), GOLD, spacing=2)
    if kind == "MAP_HOME":
        miles = int(2551 * prog)
        if FMT == "V":
            text_center(d, oy + mh + 40, f"{miles:,} MILES", font(MB, 96), WHITE, stroke=6)
            text_center(d, oy + mh + 160, "Route shown is approximate", font(MM, 26), (190, 190, 190))
        else:
            text_center(d, oy + mh - 10, f"{miles:,} MILES", font(MB, 72), WHITE, stroke=6, x=ox + mw - 230)
            text_center(d, oy + mh + 72, "Route shown is approximate", font(MM, 22), (190, 190, 190), x=ox + mw - 230)
    return can, None

STILL_BG = None
def still_bg():
    global STILL_BG
    if STILL_BG is None:
        r = VideoReader(SRC[cfg.STILL[0]], cfg.STILL[1], cfg.STILL[1] + 0.2, cfg.STILL[2] if len(cfg.STILL) > 2 else None); im, _ = r.next(); r.p.kill()
        STILL_BG = blur_bg(im, 0.35)
    return STILL_BG.copy()

def render_stat(big, small, lt, dur):
    can = still_bg(); d = ImageDraw.Draw(can)
    a = ease(lt / 0.5) * ease((dur - lt) / 0.3)
    if re.fullmatch(r"~?[\d,]+\+?", big):
        num = re.sub(r"[^\d]", "", big); prefix = "~" if big.startswith("~") else ""
        val = int(int(num) * ease(lt / 1.6))
        s = f"{prefix}{val:,}" + ("+" if big.endswith("+") else "")
    else:
        s = big
    cy = WIN_C[1] - (140 if FMT == "V" else 120)
    f = font(MB, 260 if FMT == "V" else 240)
    text_center(d, cy - 40 + (1 - a) * 30, s, f, GOLD, stroke=8)
    fs = font(MXB, 56 if FMT == "V" else 58)
    while d.textlength(small, font=fs) + 2 * len(small) > W - 90: fs = font(MXB, fs.size - 2)
    text_center(d, cy + (260 if FMT == "V" else 240), small, fs, WHITE, stroke=4, spacing=2)
    return can, None

def render_chapter(n, title, lt, dur):
    can = vignette(); d = ImageDraw.Draw(can)
    a = ease(lt / 0.5) * ease((dur - lt) / 0.4); rise = (1 - ease(lt / 0.7)) * 40
    cy = WIN_C[1] - 60
    ov = Image.new("RGBA", can.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    txt = f"CHAPTER {n}"; f1 = font(MSB, 42); widths = [od.textlength(c, font=f1) for c in txt]; sp = 14
    xx = W / 2 - (sum(widths) + sp * (len(txt) - 1)) / 2
    for c, cw in zip(txt, widths): od.text((xx, cy - 110 + rise), c, font=f1, fill=GOLD + (int(255 * a),)); xx += cw + sp
    f2 = font(PF, 104 if FMT == "V" else 120)
    lines = wrap(od, title, f2, W - 140)
    for i, l in enumerate(lines):
        tw = od.textlength(l, font=f2); od.text((W / 2 - tw / 2, cy - 30 + i * 120 + rise), l, font=f2, fill=(255, 255, 255, int(255 * a)))
    lw = 260 * ease((lt - 0.2) / 0.8)
    yl = cy + 120 + (len(lines) - 1) * 120 + rise
    od.rectangle([W / 2 - lw, yl, W / 2 + lw, yl + 4], fill=GOLD + (int(255 * a),))
    can.paste(ov, (0, 0), ov)
    return can, None

def render_cta(k, lt, dur):
    can = still_bg(); d = ImageDraw.Draw(can)
    a = ease(lt / 0.5)
    cy = WIN_C[1]
    if k == 0:
        bw, bh = (620, 150) if FMT == "V" else (640, 150)
        sc = 1 + 0.04 * math.sin(lt * 4) * ease((lt - 0.6) / 0.3)
        bw2, bh2 = bw * sc, bh * sc
        d.rounded_rectangle([W / 2 - bw2 / 2, cy - bh2 / 2, W / 2 + bw2 / 2, cy + bh2 / 2], int(bh2 / 2), fill=(225, 30, 40))
        text_center(d, cy - 42, "SUBSCRIBE", font(MB, int(78 * sc)), WHITE)
        # bell
        bx, by = W / 2 + bw2 / 2 + 70, cy
        if bx + 50 < W:
            d.ellipse([bx - 44, by - 44, bx + 44, by + 44], fill=(255, 255, 255))
            d.polygon([(bx - 20, by + 14), (bx - 16, by - 12), (bx, by - 24), (bx + 16, by - 12), (bx + 20, by + 14)], fill=(30, 30, 30))
            d.ellipse([bx - 6, by + 14, bx + 6, by + 26], fill=(30, 30, 30))
        text_center(d, cy - 260, "MORE TRUE STORIES OF", font(MXB, 50), WHITE, stroke=3)
        text_center(d, cy - 195, "INCREDIBLE DOGS", font(MB, 64), GOLD, stroke=3)
    else:
        bw, bh = (900, 420) if FMT == "V" else (1200, 380)
        x0, y0 = W / 2 - bw / 2, cy - bh / 2 - 40
        d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], 40, fill=(250, 250, 250))
        d.polygon([(x0 + 120, y0 + bh - 2), (x0 + 110, y0 + bh + 70), (x0 + 210, y0 + bh - 2)], fill=(250, 250, 250))
        f = font(MXB, 58 if FMT == "V" else 60)
        lines = wrap(d, getattr(cfg, "CTA_Q", "What's the most loyal thing YOUR dog has ever done?"), f, bw - 100)
        for i, l in enumerate(lines): text_center(d, y0 + 70 + i * 80, l, f, (20, 20, 20))
        text_center(d, y0 + bh + 110, "TELL US IN THE COMMENTS", font(MB, 52), GOLD, stroke=3, spacing=2)
    return can, None

# ------------------------------------------------------------------ main loop
def compose_footage(fr, lt, dur, credit, hold_zoom):
    z = 1.0 + 0.06 * (lt / max(dur, 0.1)) if hold_zoom else 1.0
    img = zoom(fr, z) if z > 1.0005 else fr
    can = blur_bg(img)
    win = frame_window(can, img, WIN_C[0], WIN_C[1], credit)
    return can, win

def render_span(idx, sp, prev_last):
    v = sp["vis"]; t0, t1 = sp["t0"], sp["t1"]
    f0, f1 = round(t0 * FPS), round(t1 * FPS); n = f1 - f0; dur = n / FPS
    if STILL_T is None:
        tmp = f"{OUT}/s{idx:03d}.part.mp4"
        enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", "-g", "60", "-r", str(FPS), tmp], stdin=subprocess.PIPE)
    reader = None; photo = None
    kind = v[0]
    if kind in SRC:
        t_out = v[4] if len(v) > 4 else v[1] + dur
        t_out = min(t_out, v[1] + dur)
        reader = VideoReader(SRC[kind], v[1], t_out, v[2])
        hold = (v[1] + dur) > t_out + 0.2
    elif kind == "PHOTO":
        im = Image.open(PHOTOS[v[1]]).convert("RGB"); pw, ph = fit(im.width, im.height, WIN_MAX)
        photo = im.resize((pw * 2, ph * 2), Image.LANCZOS)
    last = None; frames_out = []
    for k in range(n):
        lt = k / FPS; gt = (f0 + k) / FPS
        want = STILL_T is None or any(abs(gt - s) < 0.5 / FPS for s in STILL_T)
        if reader:
            fr, ended = reader.next()
            if fr is None: fr = Image.new("RGB", (reader.w, reader.h))
            if not want: continue_needed = True
            can, win = compose_footage(fr, lt, dur, v[3], hold) if want or k == n - 1 else (None, None)
        elif photo is not None:
            if not want and k != n - 1: can = None
            else:
                pw, ph = photo.width // 2, photo.height // 2
                img = zoom(photo, 1.0 + 0.08 * lt / dur, size=(pw, ph), pan=(0.5, 0.45))
                can = blur_bg(img); win = frame_window(can, img, WIN_C[0], WIN_C[1], v[3])
        elif kind in ("MAP_OUT", "MAP_HOME", "MAP_PIN", "MAP_ROUTE"):
            cfg._route_key = v[1]
            can, win = render_map(kind, lt, dur) if want or k == n - 1 else (None, None)
        elif kind == "STAT": can, win = render_stat(v[1], v[2], lt, dur) if want or k == n - 1 else (None, None)
        elif kind == "CHAPTER": can, win = render_chapter(v[1], v[2], lt, dur) if want or k == n - 1 else (None, None)
        elif kind == "CTA": can, win = render_cta(v[1], lt, dur) if want or k == n - 1 else (None, None)
        if can is None: continue
        draw_overlays(can, gt, win if kind in SRC or kind == "PHOTO" else None)
        # crossfade from previous span (inside this file)
        xf = 0.0 if kind == "CHAPTER" and False else 0.35
        if prev_last is not None and lt < xf:
            can = Image.blend(prev_last, can, ease(lt / xf))
        draw_captions(can, gt)
        last = can
        if STILL_T is None: enc.stdin.write(can.tobytes())
        else: frames_out.append((gt, can))
    if reader: reader.p.kill()
    if STILL_T is None:
        enc.stdin.close(); enc.wait()
        if enc.returncode == 0: os.replace(tmp, f"{OUT}/s{idx:03d}.mp4")
        else: raise SystemExit(f"encode failed span {idx}")
    return last, frames_out

if __name__ == "__main__":
    prev = None; previews = []
    spans = tl["spans"]
    for i, sp in enumerate(spans):
        if ONLY is not None and i not in ONLY:
            continue
        if STILL_T is not None and not any(sp["t0"] <= s < sp["t1"] for s in STILL_T): continue
        prev_in = prev if (ONLY is None or (i - 1) in ONLY) else None
        if ONLY is not None and prev_in is None and i > 0:
            ps = spans[i - 1]; lastt = (round(ps["t1"] * FPS) - 1) / FPS
            STILL_T = [lastt]; _, fo0 = render_span(i - 1, ps, None); STILL_T = None
            prev_in = fo0[-1][1] if fo0 else None
        last, fo = render_span(i, sp, prev_in)
        prev = last; previews += fo
        print(f"[{FMT}] span {i}/{len(spans)-1} done", flush=True)
    for gt, im in previews:
        im.save(f"{OUT}/preview_{gt:06.2f}.jpg", quality=88)
