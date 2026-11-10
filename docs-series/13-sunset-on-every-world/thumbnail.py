"""YouTube thumbnails for 13: the blue Martian sunset over rust-red ground.
python3 thumbnail.py -> out/thumb.jpg (1280x720);  VERT=1 python3 thumbnail.py -> out/thumb-vertical.jpg (1080x1920)"""
from comp import *
from PIL import ImageFilter
pl = plate("mars"); ov = Overlay()
img, ex = sh_mars(0, 0, ov, 2.1, 2.1)
if not VERT: img = zoom(img, 1.3, 0, H)
y = tonemap(anamorphic(bloom(img, 1.3), thr=3.0, amt=0.03), 1.45)
# thumbnail grade: more saturation and contrast than the film (small-size legibility)
lum = (y @ np.array([0.2126, 0.7152, 0.0722], f32))[..., None]; y = np.clip(lum + (y - lum) * 1.55, 0, 1); y = np.clip((y - 0.5) * 1.18 + 0.5, 0, 1)
base = Image.fromarray((y * 255).astype(np.uint8)).resize((W * 2, H * 2) if VERT else (2560, 1440), Image.LANCZOS)
def F(sz, w="Black"): return ImageFont.truetype(f"/usr/share/fonts/opentype/inter/InterDisplay-{w}.otf", sz)
def layer_text(im, items):
    sh = Image.new("L", im.size, 0); ds = ImageDraw.Draw(sh)
    for (xy, s, f, col) in items: ds.text((xy[0] + 8, xy[1] + 12), s, font=f, fill=255, stroke_width=14, stroke_fill=255)
    sh = sh.filter(ImageFilter.GaussianBlur(22))
    im = Image.composite(Image.new("RGB", im.size, (0, 0, 0)), im, sh.point(lambda p: int(p * 0.8)))
    d = ImageDraw.Draw(im)
    for (xy, s, f, col) in items: d.text(xy, s, font=f, fill=col, stroke_width=5, stroke_fill=(10, 8, 8))
    return im
Yc = (255, 206, 0); Wc = (255, 255, 255)
os.makedirs("out", exist_ok=True)
if VERT:
    im = layer_text(base, [((110, 400), "MARS", F(520), Yc), ((110, 910), "SUNSETS", F(390), Yc), ((110, 1300), "ARE BLUE", F(360), Yc), ((124, 2900), "and it gets stranger", F(150, "SemiBold"), Wc)])
    im.resize((1080, 1920), Image.LANCZOS).save("out/thumb-vertical.jpg", quality=93)
else:
    im = layer_text(base, [((70, 40), "MARS", F(380), Yc), ((70, 410), "SUNSETS", F(270), Yc), ((70, 690), "ARE BLUE", F(270), Yc), ((86, 1250), "and it gets stranger", F(112, "SemiBold"), Wc)])
    im.resize((1280, 720), Image.LANCZOS).save("out/thumb.jpg", quality=93)
print("ok")
