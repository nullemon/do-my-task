"""YouTube thumbnails: python3 thumb.py -> out/thumb.jpg (1280x720); MOON_VERT=1 python3 thumb.py -> out/thumb-vertical.jpg (1080x1920)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from lib import *
from PIL import ImageFilter
import comp
V = VERT
img = render_sky(comp.SKY_R, FL(54), gain=0.8, mw_gain=1.6).copy()
sun = norm([0.66, 0.30, 0.50])
if not V: mp = (560, 600, 520); ep = (1560, 250, 150)
else: mp = (470, 1010, 470); ep = (830, 380, 135)
draw_earth(img, ep[0], ep[1], ep[2], comp.art_M(-25, 18, roll=-18), sun, night_gain=1.3, exposure=1.1)
draw_moon(img, mp[0], mp[1], mp[2], comp.art_M(-12, 6, roll=14), sun, exposure=1.12, relief=1.25)
# faint dashed line of recession between the two
L = Lines(); n = 200; k = np.linspace(0, 1, n)
a = np.array(mp[:2]) + (np.array(ep[:2]) - np.array(mp[:2])) * (mp[2] + 14) / np.hypot(ep[0] - mp[0], ep[1] - mp[1]); b = np.array(ep[:2]) - (np.array(ep[:2]) - np.array(mp[:2])) * (ep[2] + 14) / np.hypot(ep[0] - mp[0], ep[1] - mp[1])
L.poly(a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, 220, 2, dash=5); L.add_to(img, (1.0, 0.84, 0.3), 0.9, 0.6)
img = bloom(img, 0.8, 0.5)
im = Image.fromarray(to8(img))
ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
B = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"; M = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"
def txt(xy, s, size, col, font=B, anchor="la", track=0):
    f = ImageFont.truetype(font, size); x, y = xy
    if anchor[0] == "m": x -= (sum(f.getlength(c) for c in s) + track * (len(s) - 1)) / 2
    for c in s: d.text((x, y), c, font=f, fill=col); x += f.getlength(c) + track
if not V:
    txt((1000, 520), "3.8 CM", 224, (255, 214, 60, 255), track=2); txt((1008, 760), "A YEAR", 150, (255, 214, 60, 255), track=6)
    txt((1012, 950), "the last total eclipse is coming", 50, (245, 247, 250, 255), font=M, track=1)
else:
    txt((540, 1340), "3.8 CM", 236, (255, 214, 60, 255), anchor="ma", track=2); txt((540, 1580), "A YEAR", 150, (255, 214, 60, 255), anchor="ma", track=6)
    txt((540, 235), "the last total eclipse is coming", 54, (245, 247, 250, 255), font=M, anchor="ma", track=1)
sh = ov.split()[3].filter(ImageFilter.GaussianBlur(14)); shadow = Image.new("RGBA", im.size, (0, 0, 0, 255)); shadow.putalpha(sh.point(lambda v: min(255, int(v * 1.6))))
im = Image.alpha_composite(Image.alpha_composite(im.convert("RGBA"), shadow), ov).convert("RGB")
if not V: im = im.resize((1280, 720), Image.LANCZOS); im.save(HERE + "/out/thumb.jpg", quality=93)
else: im.save(HERE + "/out/thumb-vertical.jpg", quality=92)
print("ok")
