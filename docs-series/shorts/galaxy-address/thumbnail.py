"""Thumbnails: out/thumb-vertical.jpg (1080x1920) and out/thumb.jpg (1280x720, a crop of the same render).
The face-on Milky Way over the observatory (halo scene), no readouts/captions, big title words in the caption style.
Usage: /home/user/ttsenv/bin/python thumbnail.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import short as V
import numpy as np
from PIL import Image
from lib.text import word_layer, composite, ORANGE

WHITE = (250, 250, 250)
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
T = V.T_SW["halo"] + 2.5


def save(img, path, size=None):
    im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
    if size: im = im.resize(size, Image.LANCZOS)
    im.save(path, quality=92); print(path, im.size)


sc = V.Scene(True)
sc.overlay = lambda *a, **k: None
base = sc.frame(T)
v = base.copy()
for w, col, size, x, y in (("WHAT IF EARTH", WHITE, 120, 540, 230), ("LIVED", ORANGE, 230, 540, 1000), ("HERE?", ORANGE, 230, 540, 1210)):
    rgba, _ = word_layer(w, size, 1020, fill=col); composite(v, rgba, x, y, 1.0)
save(v, os.path.join(OUT, "thumb-vertical.jpg"))
h = base[380:380 + 608].copy()
for w, col, size, x, y in (("WHAT IF EARTH LIVED HERE?", ORANGE, 92, 540, 80),):
    rgba, _ = word_layer(w, size, 1040, fill=col); composite(h, rgba, x, y, 1.0)
save(h, os.path.join(OUT, "thumb.jpg"), (1280, 720))
