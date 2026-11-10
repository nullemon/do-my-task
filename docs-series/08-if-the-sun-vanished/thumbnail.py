"""YouTube thumbnail (1280x720) for 08: half-lit Earth, the Sun-facing side already going black, '8 MIN 20 SEC'.
The dark front is drawn as it would arrive: a plane perpendicular to the Sun's direction, reaching the sub-solar point first.
Run: python3 thumbnail.py  ->  out/thumb.jpg"""
import os
from lib import *
from PIL import ImageFilter
img = sky_view(1500, 1250, 0.85, 14) * 0.7
L = norm([-0.74, 0.20, 0.64]); cx, cy, R, lon0 = 1440, 548, 468, math.radians(8)
lit = img.copy(); drk = img.copy()
g = earth(lit, cx, cy, R, lon0, L, cloud_t=0.02)
earth(drk, cx, cy, R, lon0, L, sun=0.0, amb=0.07, lights=1.0, lights_day=0.5, cloud_t=0.02)
yy, xx = np.mgrid[0:H, 0:W].astype(f32)
u = (xx - cx) / R; v = -(yy - cy) / R; z = np.sqrt(np.clip(1 - u * u - v * v, 0, 1)); ndl = u * L[0] + v * L[1] + z * L[2]
front = 0.60                                   # everything with n.L above this has already lost the Sun
m = smooth(front - 0.012, front + 0.012, ndl)[..., None]
inside = ((u * u + v * v) < 1.0)[..., None]
planet = lit * (1 - m) + drk * m
edge = np.exp(-((ndl - front) / 0.012) ** 2)[..., None] * inside * np.array([1.0, 0.75, 0.35], f32) * 0.9      # the last rim of sunlight
halo_keep = 1 - smooth(front - 0.2, front + 0.1, ndl)[..., None] * (~inside)
aa = np.clip((1 - np.sqrt(u * u + v * v)) * R + 0.5, 0, 1)[..., None]
img = (lit * halo_keep + img * (1 - halo_keep)) * (1 - aa) + planet * aa + edge * aa
y = tonemap(anamorphic(bloom(img)), 1.08)
base = Image.fromarray((np.clip(y, 0, 1) * 255).astype(np.uint8)).resize((2560, 1440), Image.LANCZOS)
def F(sz, w="Black"): return ImageFont.truetype(f"/usr/share/fonts/opentype/inter/InterDisplay-{w}.otf", sz)
def layer_text(im, items):
    sh = Image.new("L", im.size, 0); ds = ImageDraw.Draw(sh)
    for (xy, s, f, col) in items: ds.text((xy[0] + 8, xy[1] + 12), s, font=f, fill=255, stroke_width=12, stroke_fill=255)
    sh = sh.filter(ImageFilter.GaussianBlur(20))
    im = Image.composite(Image.new("RGB", im.size, (0, 0, 0)), im, sh.point(lambda p: int(p * 0.85)))
    d = ImageDraw.Draw(im)
    for (xy, s, f, col) in items: d.text(xy, s, font=f, fill=col, stroke_width=5, stroke_fill=(8, 8, 16))
    return im
Y = (255, 206, 0)
im = layer_text(base, [((100, 230), "8 MIN", F(400), Y), ((100, 640), "20 SEC", F(400), Y), ((112, 1100), "then everything changes", F(112, "SemiBold"), (255, 255, 255))])
os.makedirs("out", exist_ok=True)
im.resize((1280, 720), Image.LANCZOS).save("out/thumb.jpg", quality=93); print("ok")
