"""Thumbnails: out/thumb-vertical.jpg (1080x1920) and out/thumb.jpg (1280x720, cropped from the same frame).
The Kepler-16 double sunset over the park with its double shadows, "IF EARTH HAD TWO SUNS" in the caption style.
Usage: /home/user/ttsenv/bin/python thumbnail.py [t]   (t = video time of the background frame)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import short as V
import numpy as np
from PIL import Image
from lib.text import word_layer, composite, ORANGE

T = float(sys.argv[1]) if len(sys.argv) > 1 else 21.2
WHITE = (250, 250, 250)
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)


def save(img, path, size=None):
    im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
    if size: im = im.resize(size, Image.LANCZOS)
    im.save(path, quality=92); print(path, im.size)


sc = V.Scene(True)
sc.overlay = lambda out, t, cur, t0, Sc: None                       # no captions / readouts / labels
base = sc.frame(T)
v = base.copy()
for w, col, size, maxw, x, y in [("IF EARTH", WHITE, 150, 1000, 540, 430), ("HAD TWO", WHITE, 150, 1000, 540, 600),
                                 ("SUNS", ORANGE, 300, 1000, 540, 830)]:
    rgba, _ = word_layer(w, size, maxw, fill=col); composite(v, rgba, x, y, 1.0)
save(v, os.path.join(OUT, "thumb-vertical.jpg"))
y0 = 960; crop = base[y0:y0 + 608].copy()                              # 1080 x 608 (16:9): suns above, lawn below
for w, col, size, maxw, x, y in [("IF EARTH HAD", WHITE, 84, 1000, 540, 400), ("TWO SUNS", ORANGE, 140, 1000, 540, 515)]:
    rgba, _ = word_layer(w, size, maxw, fill=col); composite(crop, rgba, x, y, 1.0)
save(crop, os.path.join(OUT, "thumb.jpg"), (1280, 720))
