"""YouTube thumbnail (1280x720): Apophis model in the foreground, Earth with the geostationary ring behind,
"32,000 KM" in yellow + "FRIDAY 13 APRIL 2029 · IT WILL MISS". Built with the film's own renderers at 1920x1080."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from comp import *
from PIL import ImageFilter
img = render_sky(look_at((0, 0, 0), norm([0.35, 0.90, 0.25])), (W / 2) / math.tan(math.radians(27)), gain=1.2, mw_gain=2.0).copy()
EX, EY, ER = 1470, 320, 200
M = art_M(-18, 33, roll=-24)
draw_earth(img, EX, EY, ER, M, SUN_AST, night_gain=1.6, exposure=1.12)
ring_art(img, EX, EY, ER, M, 0.0, gain=3.0, line=1.0)
# marker for the pass, inside the ring
az = math.radians(-70); pb = np.array([math.cos(az), math.sin(az), 0.30]) * (TL.RP / TL.RE) * ER
pc = M.T @ pb; mx, my = EX + pc[0], EY - pc[1]
put_sprite(img, ast_at(int(sys.argv[1]) if len(sys.argv) > 1 else 30), 610, 640, 1.16, angle=-10, gain=1.12)
img = bloom(img, 0.75, 0.6)
yy, xx = np.mgrid[0:H, 0:W].astype(F32)
img *= (1 - 0.45 * np.clip(((xx - W * 0.5) / (W * 0.8)) ** 2 + ((yy - H * 0.5) / (H * 0.85)) ** 2, 0, 1))[..., None]
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


Y = (255, 206, 0)
im = layer_text(base, [((846, 622), "32,000 KM", font_b(176), Y),
                       ((70, 56), "CLOSER THAN", font_b(112), (255, 255, 255)),
                       ((70, 180), "OUR SATELLITES", font_b(112), (255, 255, 255)),
                       ((854, 836), "FRIDAY 13 APRIL 2029  ·  IT WILL MISS", font_b(47, "Bold"), (255, 255, 255))])
os.makedirs(HERE + "/out", exist_ok=True)
im.resize((1280, 720), Image.LANCZOS).save(HERE + "/out/thumb.jpg", quality=93)
print("ok")
