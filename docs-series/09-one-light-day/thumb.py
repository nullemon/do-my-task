"""YouTube thumbnail (1280x720): our Voyager model against the Milky Way, a tiny pale-blue Earth dot, '1 LIGHT-DAY'.
Composed at 1920x1080 with the film's own compositor pieces, then reduced."""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from lib import *
import sky as SKY
from comp import SkyPlate, finish, plate
HERE = os.path.dirname(os.path.abspath(__file__))
V = VERT
sk = SkyPlate(SKY.look_at_dir(SKY.gal_dir(18, 9), 70 if V else 34), 50, margin=1.05, mw=0.8, stars=1.4)
lin = sk.crop(0, 0)
p = plate("plate_thumb")
if V: rgb, al = p.place(0.66, 560, 1130, 0.555, 0.40)
else: rgb, al = p.place(W / p.w * 1.42, W * 0.70, H * 0.56)
# tiny pale-blue dot with a soft glow
ex, ey = (170, 930) if V else (250, 820)
glow_dot(lin, ex, ey, 3.0, 2.6, (0.55, 0.75, 1.0)); glow_dot(lin, ex, ey, 0.25, 22, (0.4, 0.6, 1.0))
over(lin, rgb, al, 0.95)
disp = finish(lin, 1.25, bl=0.5, br=18, thresh=0.35)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
disp *= (1 - 0.45 * np.clip(((xx - W * 0.55) / (W * 0.8)) ** 2 + ((yy - H * 0.5) / (H * 0.85)) ** 2, 0, 1))[..., None]
im = Image.fromarray(to8(disp))
def font(sz, w="Black"):
    return ImageFont.truetype(f"/usr/share/fonts/opentype/inter/InterDisplay-{w}.otf", sz)
def layer_text(im, items):
    sh = Image.new("L", im.size, 0); ds = ImageDraw.Draw(sh)
    for (xy, s, f, col) in items: ds.text((xy[0] + 6, xy[1] + 9), s, font=f, fill=255, stroke_width=9, stroke_fill=255)
    sh = sh.filter(ImageFilter.GaussianBlur(16))
    im = Image.composite(Image.new("RGB", im.size, (0, 0, 0)), im, sh.point(lambda v: int(v * 0.85)))
    d = ImageDraw.Draw(im)
    for (xy, s, f, col) in items: d.text(xy, s, font=f, fill=col, stroke_width=4, stroke_fill=(8, 8, 16))
    return im
Y = (255, 206, 0)
if V:
    im = layer_text(im, [((70, 250), "1 LIGHT-", font(232), Y), ((70, 470), "DAY", font(232), Y), ((78, 1500), "FROM EARTH", font(120), (255, 255, 255)),
                         ((82, 1650), "49 years to get here", font(66, "SemiBold"), (255, 255, 255))])
else:
    im = layer_text(im, [((80, 70), "1 LIGHT-DAY", font(236), Y), ((92, 340), "FROM EARTH", font(112), (255, 255, 255)),
                         ((96, 500), "49 years to get here", font(62, "SemiBold"), (255, 255, 255))])
d = ImageDraw.Draw(im)
d.line([(ex + 16, ey - 16), (ex + 70, ey - 70)], fill=(230, 230, 235), width=3)
d.text((ex + 80, ey - 110), "EARTH", font=font(40, "Bold"), fill=(230, 235, 255), stroke_width=3, stroke_fill=(8, 8, 16))
if V:
    out = os.path.join(HERE, "out", "thumb-vertical.jpg"); im.save(out, quality=93, subsampling=0)
else:
    out = os.path.join(HERE, "out", "thumb.jpg"); im.resize((1280, 720), Image.LANCZOS).save(out, quality=93, subsampling=0)
print(out, os.path.getsize(out))
