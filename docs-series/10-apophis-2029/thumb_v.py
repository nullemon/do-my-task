"""Vertical cover (1080x1920): same promise as thumb.jpg, recomposed - Earth and ring above, Apophis model below, the number
and the reassurance inside the phone-safe area."""
import os, sys
os.environ["APO_VERT"] = "1"
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from comp_v import *
from PIL import ImageFilter
img = render_sky(look_at((0, 0, 0), norm([0.35, 0.90, 0.25])), FL(54), gain=1.2, mw_gain=2.0).copy()
EX, EY, ER = 700, 690, 215
M = art_M(-18, 33, roll=-24)
draw_earth(img, EX, EY, ER, M, SUN_AST, night_gain=1.6, exposure=1.12)
ring_art(img, EX, EY, ER, M, 0.0, gain=3.0, line=1.0)
put_sprite(img, ast_at(30), 500, 1130, 0.86, angle=-14, gain=1.12)
img = bloom(img, 0.75, 0.6)
yy, xx = np.mgrid[0:H, 0:W].astype(F32)
img *= (1 - 0.45 * np.clip(((xx - W * 0.5) / (W * 0.85)) ** 2 + ((yy - H * 0.5) / (H * 0.8)) ** 2, 0, 1))[..., None]
base = Image.fromarray((np.clip(img, 0, 1) ** 0.92 * 255).astype(np.uint8))


def font_b(sz, w="Black"):
    for p in (f"/usr/share/fonts/opentype/inter/InterDisplay-{w}.otf", f"/usr/share/fonts/opentype/inter/Inter-{w}.otf"):
        try: return ImageFont.truetype(p, sz)
        except OSError: pass


def layer_text(im, items):
    sh = Image.new("L", im.size, 0); ds = ImageDraw.Draw(sh); out = []
    for (y, s, f, col) in items:
        w = ds.textlength(s, font=f); out.append(((W - w) / 2, y, s, f, col))
    for (x, y, s, f, col) in out: ds.text((x + 6, y + 9), s, font=f, fill=255, stroke_width=8, stroke_fill=255)
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    im = Image.composite(Image.new("RGB", im.size, (0, 0, 0)), im, sh.point(lambda p: int(p * 0.85)))
    d = ImageDraw.Draw(im)
    for (x, y, s, f, col) in out: d.text((x, y), s, font=f, fill=col, stroke_width=4, stroke_fill=(8, 8, 16))
    return im


Y = (255, 206, 0)
im = layer_text(base, [(250, "CLOSER THAN", font_b(112), (255, 255, 255)), (372, "OUR SATELLITES", font_b(112), (255, 255, 255)),
                       (1270, "32,000 KM", font_b(190), Y), (1476, "FRIDAY 13 APRIL 2029  ·  IT WILL MISS", font_b(44, "Bold"), (255, 255, 255))])
im.save(HERE + "/out/thumb-vertical.jpg", quality=93); print("ok")
