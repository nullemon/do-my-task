"""Thumbnails: out/thumb.jpg (1280x720) and out/thumb-vertical.jpg (1080x1920).
The Sun 27 deg wide over the molten desert, "IF EARTH SKIMMED THE SUN" in the caption style.
Usage: /home/user/ttsenv/bin/python thumbnail.py [t]   (t = video time of the background frame)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import short as V
import numpy as np
from PIL import Image
from lib.text import word_layer, composite, ORANGE

T = float(sys.argv[1]) if len(sys.argv) > 1 else 38.0
WHITE = (250, 250, 250)
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
sc = V.Scene()
sc.overlay = lambda out, t, cur, t0: None
sc.today_ring = lambda out, t, a: None
img = sc.frame(T)


def save(im, path, size=None):
    im = Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8))
    if size: im = im.resize(size, Image.LANCZOS)
    im.save(path, quality=92); print(path, im.size)


v = img.copy()
for w, col, size, maxw, x, y in [("IF EARTH", WHITE, 130, 1000, 540, 1080), ("SKIMMED", ORANGE, 220, 1020, 540, 1260), ("THE SUN", ORANGE, 220, 1020, 540, 1450)]:
    rgba, _ = word_layer(w, size, maxw, fill=col); composite(v, rgba, x, y, 1.0)
save(v, os.path.join(OUT, "thumb-vertical.jpg"))
# 16:9: crop the band with the Sun and the lava horizon, text on the right half
W = np.zeros((720, 1280, 3), np.float32)
band = img[150:150 + 1215]                                                   # 1080 x 1215 -> scale to 640 x 720
from PIL import Image as I
b = np.asarray(I.fromarray((np.clip(band, 0, 1) * 255).astype(np.uint8)).resize((640, 720), I.LANCZOS)).astype(np.float32) / 255
W[:, :640] = b
bg = np.asarray(I.fromarray((np.clip(img[1250:1250 + 700], 0, 1) * 255).astype(np.uint8)).resize((640, 720), I.LANCZOS)).astype(np.float32) / 255
W[:, 640:] = bg * 0.75
for w, col, size, maxw, x, y in [("IF EARTH", WHITE, 92, 600, 960, 190), ("SKIMMED", ORANGE, 150, 620, 960, 350), ("THE SUN", ORANGE, 150, 620, 960, 520)]:
    rgba, _ = word_layer(w, size, maxw, fill=col); composite(W, rgba, x, y, 1.0)
save(W, os.path.join(OUT, "thumb.jpg"))
