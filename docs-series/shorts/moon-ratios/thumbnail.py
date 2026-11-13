"""Thumbnails: out/thumb-vertical.jpg (1080x1920) and out/thumb.jpg (1280x720, cropped from a 9:16 frame on a blurred
fill). The huge Charon-ratio Moon over the park, "IF OUR MOON WAS LIKE CHARON" in the caption style.
Usage: /home/user/ttsenv/bin/python thumbnail.py [t]   (t = video time of the background frame)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import short as V
import numpy as np, cv2
from PIL import Image
from lib.text import word_layer, composite, ORANGE

T = float(sys.argv[1]) if len(sys.argv) > 1 else 29.0
WHITE = (250, 250, 250)
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)


def save(img, path):
    im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)); im.save(path, quality=92); print(path, im.size)


sc = V.Scene(True)
sc.overlay = lambda out, t, cur, t0, la=0.0: None               # no captions / readouts
base = sc.frame(T)
v = base.copy()
for w, col, size, maxw, x, y in [("IF OUR MOON", WHITE, 130, 1000, 540, 1000), ("WAS LIKE", ORANGE, 170, 1020, 540, 1170),
                                 ("CHARON", ORANGE, 250, 1040, 540, 1370)]:
    rgba, _ = word_layer(w, size, maxw, fill=col); composite(v, rgba, x, y, 1.0)
save(v, os.path.join(OUT, "thumb-vertical.jpg"))
# 16:9: the Moon + park band of the vertical frame on the right, over a blurred, darkened fill; text on the left
crop = base[220:1520]                                           # 1080 x 1300
H, W = 720, 1280
bg = cv2.GaussianBlur(cv2.resize(base[200:920], (W, H)), (0, 0), 25) * 0.7
s = H / crop.shape[0]; cw = int(crop.shape[1] * s)
fg = cv2.resize(crop, (cw, H), interpolation=cv2.INTER_AREA)
x0 = W - cw - 20
bg[:, x0:x0 + cw] = fg
m = np.clip(np.arange(cw) / 60, 0, 1)[None, :, None]           # soft left edge
bg[:, x0:x0 + cw] = fg * m + bg[:, x0:x0 + cw] * (1 - m)
w_ = bg.copy()
for w, col, size, maxw, x, y in [("IF OUR MOON", WHITE, 84, 640, 360, 210), ("WAS LIKE", ORANGE, 120, 660, 360, 340),
                                 ("CHARON", ORANGE, 170, 660, 360, 500)]:
    rgba, _ = word_layer(w, size, maxw, fill=col); composite(w_, rgba, x, y, 1.0)
save(w_, os.path.join(OUT, "thumb.jpg"))
