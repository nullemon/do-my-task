"""YouTube thumbnails: 16:9 (out/thumb.jpg, 1280x720) and, with NS_VERT=1, 9:16 (out/thumb-vertical.jpg, 1080x1920).
The film's own opening picture: the Blender teaspoon holding a blinding blue-white speck above the Earth's limb,
"1 TEASPOON" in yellow and "= A MOUNTAIN" in white."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from comp import *
from PIL import ImageFilter
img = earth_plate(6.0, "thumb", apex=hv(800, 1330), exposure=1.08)
bx, by, sc, ang = hv((590, 600, 1.12, -5.0), (300, 1080, 1.0, 20.0))
spoon(img, 0.3, bx, by, sc, ang, bead=1.0, gain=1.08)
glare(img, bx, by, 1.0, s=1.4)
img = bloom(img, 0.70, 0.75)
yy, xx = np.mgrid[0:H, 0:W].astype(F32)
img *= (1 - 0.40 * np.clip(((xx - W * 0.5) / (W * 0.8)) ** 2 + ((yy - H * 0.5) / (H * 0.85)) ** 2, 0, 1))[..., None]
img = np.clip(img, 0, 1) ** 0.92
base = Image.fromarray((img * 255).astype(np.uint8))


def font_b(sz, w="Black"):
    for p in (f"/usr/share/fonts/opentype/inter/InterDisplay-{w}.otf", f"/usr/share/fonts/opentype/inter/Inter-{w}.otf"):
        try: return ImageFont.truetype(p, sz)
        except OSError: pass


def layer_text(im, items):
    sh = Image.new("L", im.size, 0); ds = ImageDraw.Draw(sh)
    for (xy, s, f, col) in items: ds.text((xy[0] + 6, xy[1] + 9), s, font=f, fill=255, stroke_width=8, stroke_fill=255)
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    im = Image.composite(Image.new("RGB", im.size, (0, 0, 0)), im, sh.point(lambda p: int(p * 0.85)))
    d = ImageDraw.Draw(im)
    for (xy, s, f, col) in items: d.text(xy, s, font=f, fill=col, stroke_width=4, stroke_fill=(8, 8, 16))
    return im


Y = (255, 206, 0); Wh = (255, 255, 255)
os.makedirs(HERE + "/out", exist_ok=True)
if VERT:
    im = layer_text(base, [((60, 250), "1 TEASPOON", font_b(146), Y),
                           ((66, 430), "= A MOUNTAIN", font_b(104), Wh), ((76, 1560), "OF A NEUTRON STAR", font_b(84, "Bold"), Wh)])
    im.save(HERE + "/out/thumb-vertical.jpg", quality=92)
else:
    im = layer_text(base, [((64, 40), "1 TEASPOON", font_b(252), Y), ((76, 318), "= A MOUNTAIN", font_b(104), Wh),
                           ((1030, 930), "OF A NEUTRON STAR", font_b(78, "Bold"), Wh)])
    im.resize((1280, 720), Image.LANCZOS).save(HERE + "/out/thumb.jpg", quality=93)
print("ok")
