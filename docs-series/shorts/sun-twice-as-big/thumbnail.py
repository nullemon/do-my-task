"""Thumbnails: out/thumb-vertical.jpg (1080x1920) and out/thumb.jpg (1280x720, a crop of the same render).
The 10x Sun over the scorched, steaming park, no readouts/captions, big title words in the caption style.
Usage: /home/user/ttsenv/bin/python thumbnail.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import short as V
import numpy as np
from PIL import Image
from lib.text import word_layer, composite, ORANGE

WHITE = (250, 250, 250)
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
T = V.T_BOIL + 1.0


def save(img, path, size=None):
    im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
    if size: im = im.resize(size, Image.LANCZOS)
    im.save(path, quality=92); print(path, im.size)


sc = V.Scene(True)
sc.overlay = lambda *a, **k: None
sc.today_ring = lambda *a, **k: None
base = sc.frame(T)
v = base.copy()
for w, col, size, x, y in (("WHAT IF THE SUN", WHITE, 110, 540, 250), ("WERE 10×", ORANGE, 220, 540, 1000), ("BIGGER?", ORANGE, 230, 540, 1220)):
    rgba, _ = word_layer(w, size, 1020, fill=col); composite(v, rgba, x, y, 1.0)
save(v, os.path.join(OUT, "thumb-vertical.jpg"))
h = base[420:420 + 608].copy()
rgba, _ = word_layer("SUN × 10", 150, 1040, fill=ORANGE); composite(h, rgba, 540, 470, 1.0)
save(h, os.path.join(OUT, "thumb.jpg"), (1280, 720))
