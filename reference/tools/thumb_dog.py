"""Reference thumbnail recipe used for the first 6 dog videos (1280x720).
Layout: colored gradient on the left (story color), real photo/frame of THE dog on the right with a feathered edge,
red 'TRUE STORY' tag, 2-3 huge headline lines (white + one yellow line), a small sub-line, optional circle+arrow.

Usage example:
  python thumb_dog.py frame.png out.jpg --crop 150,0,600,338 --lines "SHE|SAVED|12 LIVES" --yellow 2 --sub "FROM THE RUBBLE" --c1 20,60,140 --c2 10,30,70
"""
import argparse, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps
FD = "fonts/"
W, H = 1280, 720
ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("out")
ap.add_argument("--crop", default=None, help="x0,y0,x1,y1 crop of the source (keep the dog's face, drop logos)")
ap.add_argument("--lines", required=True, help="headline lines separated by |")
ap.add_argument("--yellow", default="-1", help="indexes of lines to color yellow, e.g. 1,2")
ap.add_argument("--sub", default="")
ap.add_argument("--c1", default="255,120,20"); ap.add_argument("--c2", default="120,30,10")
ap.add_argument("--sepia", action="store_true", help="for old black & white photos")
ap.add_argument("--circle", default=None, help="cx,cy,r circle + arrow onto a face (output coords)")
ap.add_argument("--size", type=int, default=100)
a = ap.parse_args()
src = Image.open(a.src).convert("RGB")
if a.crop: src = src.crop(tuple(map(int, a.crop.split(","))))
if a.sepia:
    src = ImageOps.colorize(ImageEnhance.Contrast(src.convert("L")).enhance(1.25), (25, 30, 45), (250, 245, 235))
else:
    src = ImageEnhance.Color(src).enhance(1.25); src = ImageEnhance.Contrast(src).enhance(1.12); src = ImageEnhance.Sharpness(src).enhance(1.5)
s = H / src.height; im = src.resize((int(src.width * s), H), Image.LANCZOS)
y, x = np.mgrid[0:H, 0:W]; t = x / W
c1 = np.array(list(map(int, a.c1.split(",")))); c2 = np.array(list(map(int, a.c2.split(","))))
can = Image.fromarray((c1 * (1 - t[..., None]) + c2 * t[..., None]).astype(np.uint8))
m = Image.new("L", im.size, 255); md = ImageDraw.Draw(m)
for i in range(130): md.line([(i, 0), (i, H)], fill=int(255 * i / 130))     # feathered left edge
can.paste(im, (W - im.width + 10, 0), m)
d = ImageDraw.Draw(can)
f1 = ImageFont.truetype(FD + "Montserrat_900Black.ttf", a.size); f3 = ImageFont.truetype(FD + "Montserrat_800ExtraBold.ttf", 36)
d.rounded_rectangle([46, 52, 340, 106], 14, fill=(200, 20, 30)); d.text((62, 58), "TRUE STORY", font=f3, fill="white")
yel = {int(k) for k in a.yellow.split(",") if k.strip() not in ("", "-1")}
yy = 150
for i, line in enumerate(a.lines.split("|")):
    d.text((40, yy), line, font=f1, fill=(255, 226, 70) if i in yel else (255, 255, 255), stroke_width=10, stroke_fill=(10, 10, 20))
    yy += int(a.size * 1.15)
if a.sub:
    d.text((46, yy + 20), a.sub, font=ImageFont.truetype(FD + "Montserrat_900Black.ttf", 42), fill="white", stroke_width=6, stroke_fill=(10, 10, 20))
if a.circle:
    cx, cy, r = map(int, a.circle.split(","))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 226, 70), width=7)
    d.line([(cx - r - 150, cy + r + 120), (cx - r + 8, cy + 10)], fill=(255, 226, 70), width=11)
can.save(a.out, quality=93)
print("saved", a.out)
