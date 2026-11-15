"""Thumbnails: out/thumb-vertical.jpg (1080x1920) and out/thumb.jpg (1280x720, a 16:9 crop of the same frame).
Usage: /home/user/ttsenv/bin/python thumbnail.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import short as V
import numpy as np
from PIL import Image
from lib.text import word_layer, composite, ORANGE

T, CROP_Y, LINES_V, LINES_W = 17.5, 280, [("IF THIS FARM", (250, 250, 250), 120, 1000, 540, 1080), ("WERE ON", (250, 250, 250), 120, 1000, 540, 1210),
                                 ("ANOTHER WORLD", ORANGE, 200, 1020, 540, 1400)], \
    [("IF THIS FARM WERE ON", (250, 250, 250), 52, 520, 300, 420), ("ANOTHER WORLD", ORANGE, 80, 520, 300, 510)]
WHITE = (250, 250, 250)
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
sc = V.Scene(True)
sc.overlay = lambda out, t, cur, t0: None                 # no captions / readouts
base = sc.frame(T)


def save(img, path, size=None):
    im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
    if size: im = im.resize(size, Image.LANCZOS)
    im.save(path, quality=92); print(path, im.size)


v = base.copy()
for w, col, size, maxw, x, y in LINES_V:
    rgba, _ = word_layer(w, size, maxw, fill=col); composite(v, rgba, x, y, 1.0)
save(v, os.path.join(OUT, "thumb-vertical.jpg"))
w = base[CROP_Y:CROP_Y + 608].copy()
for t_, col, size, maxw, x, y in LINES_W:
    rgba, _ = word_layer(t_, size, maxw, fill=col); composite(w, rgba, x, y, 1.0)
save(w, os.path.join(OUT, "thumb.jpg"), (1280, 720))
