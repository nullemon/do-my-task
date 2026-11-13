"""python lib/thumbs.py <code>  -> deliver/<Dog> - YouTube Thumbnail 16x9.jpg + <Dog> - Shorts Thumbnail 9x16.jpg
cfg.THUMB = dict(photo=key, crop=(x0,y0,x1,y1), face=(u,v) of the dog's face in the cropped photo, lines=[...], yellow={i}, sub="...",
                 c1=(r,g,b), c2=(r,g,b), sepia=True)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_case, font, MB, MXB
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageOps, ImageFilter
YEL, INK, RED = (255, 222, 60), (10, 10, 20), (205, 20, 30)
cfg, _ = load_case(sys.argv[1]); T = cfg.THUMB
src = Image.open(cfg.PH[T["photo"]]["file"]).convert("RGB")
if T.get("crop"): src = src.crop(T["crop"])
if T.get("sepia"): src = ImageOps.colorize(ImageEnhance.Contrast(ImageOps.autocontrast(src.convert("L"), 1)).enhance(1.15), (22, 18, 14), (252, 242, 222), mid=(160, 136, 104))
else: src = ImageEnhance.Contrast(ImageEnhance.Color(src).enhance(1.25)).enhance(1.1)
src = src.filter(ImageFilter.UnsharpMask(2, 80, 2))
out = os.path.join(cfg.DIR, "deliver"); os.makedirs(out, exist_ok=True)

def headline(d, x, y, maxw, size, center=False):
    for i, line in enumerate(T["lines"]):
        f = font(MB, size)
        while d.textlength(line, font=f) > maxw: f = font(MB, f.size - 4)
        tw = d.textlength(line, font=f); xx = x - tw / 2 if center else x
        d.text((xx, y), line, font=f, fill=YEL if i in T["yellow"] else (255, 255, 255), stroke_width=max(8, f.size // 10), stroke_fill=INK)
        y += int(f.size * 1.12)
    return y

# ---- YouTube 1280x720: gradient left, dog right 58 %, feathered edge
W, H = 1280, 720
s = max(H / src.height, W * 0.60 / src.width); im = src.resize((int(src.width * s), int(src.height * s)), Image.LANCZOS)
fv = T["face"][1] * im.height; yo = int(min(max(fv - H * 0.32, 0), im.height - H)); im = im.crop((0, yo, im.width, yo + H))
fu = T["face"][0] * im.width; target = W * 0.70
xoff = int(min(max(target - fu, W - im.width), W * 0.40))
y, x = np.mgrid[0:H, 0:W]; t = (x / W)[..., None]
can = Image.fromarray((np.array(T["c1"]) * (1 - t) + np.array(T["c2"]) * t).astype(np.uint8))
m = Image.new("L", im.size, 255); md = ImageDraw.Draw(m)
for i in range(160): md.line([(i, 0), (i, H)], fill=int(255 * i / 160))
can.paste(im, (xoff, 0), m)
d = ImageDraw.Draw(can)
d.rounded_rectangle([46, 46, 336, 102], 14, fill=RED); d.text((64, 52), "TRUE STORY", font=font(MXB, 36), fill="white")
yy = headline(d, 40, 150, W * 0.47, 150)
if T.get("sub"):
    f = font(MB, 40)
    while d.textlength(T["sub"], font=f) > W * 0.47: f = font(MB, f.size - 2)
    d.text((46, yy + 18), T["sub"], font=f, fill="white", stroke_width=6, stroke_fill=INK)
can.save(os.path.join(out, f"{cfg.DOG} - YouTube Thumbnail 16x9.jpg"), quality=93)

# ---- Shorts 1080x1920: face fills the top 55 %, headline centered below
W, H = 1080, 1920; top = int(H * 0.60)
s = max(W / src.width, top / src.height) * T.get("zoom9", 1.0); im = src.resize((int(src.width * s), int(src.height * s)), Image.LANCZOS)
fx, fy = T["face"][0] * im.width, T["face"][1] * im.height
x0 = int(min(max(fx - W / 2, 0), im.width - W)); y0 = int(min(max(fy - top * 0.45, 0), im.height - top))
can = Image.new("RGB", (W, H)); can.paste(im.crop((x0, y0, x0 + W, y0 + top)), (0, 0))
y, x = np.mgrid[0:H - top + 200, 0:W]; t = (y / (H - top + 200))[..., None]
bot = Image.fromarray((np.array(T["c1"]) * (1 - t) + np.array(T["c2"]) * t).astype(np.uint8))
fade = Image.new("L", bot.size, 255); fd = ImageDraw.Draw(fade)
for i in range(200): fd.line([(0, i), (W, i)], fill=int(255 * i / 200))
can.paste(bot, (0, top - 200), fade)
d = ImageDraw.Draw(can)
d.rounded_rectangle([W / 2 - 170, top - 30, W / 2 + 170, top + 34], 14, fill=RED)
d.text((W / 2 - d.textlength("TRUE STORY", font=font(MXB, 40)) / 2, top - 24), "TRUE STORY", font=font(MXB, 40), fill="white")
yy = headline(d, W / 2, top + 90, W * 0.88, 200, center=True)
if T.get("sub"):
    f = font(MB, 52)
    while d.textlength(T["sub"], font=f) > W * 0.9: f = font(MB, f.size - 2)
    d.text((W / 2 - d.textlength(T["sub"], font=f) / 2, yy + 26), T["sub"], font=f, fill="white", stroke_width=6, stroke_fill=INK)
can.save(os.path.join(out, f"{cfg.DOG} - Shorts Thumbnail 9x16.jpg"), quality=93)
print("thumbnails written to", out)
