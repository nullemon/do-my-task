"""Thumbnails: out/thumb.jpg (1280x720) and out/thumb-vertical.jpg (1080x1920).
The Orion Nebula blazing over the city skyline, "IF NEBULAS WERE CLOSER" in the caption style.
Usage: /home/user/ttsenv/bin/python thumbnail.py [t]   (t = video time of the background frame)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import short as V
import numpy as np
from PIL import Image
from lib.text import word_layer, composite, ORANGE

T = float(sys.argv[1]) if len(sys.argv) > 1 else 5.6
WHITE = (250, 250, 250)
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)


def save(img, path, size=None):
    im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
    if size: im = im.resize(size, Image.LANCZOS)
    im.save(path, quality=92); print(path, im.size)


def render(vertical, lines):
    sc = V.Scene(vertical)
    sc.overlay = lambda out, t, cur, t0, ghost: None        # no captions / readouts
    img = sc.frame(T)
    for w, col, size, maxw, x, y in lines:
        rgba, _ = word_layer(w, size, maxw, fill=col)
        composite(img, rgba, x, y, 1.0)
    return img


v = render(True, [("IF", WHITE, 130, 1000, 540, 980), ("NEBULAS", ORANGE, 230, 1020, 540, 1160),
                  ("WERE", WHITE, 130, 1000, 540, 1340), ("CLOSER", ORANGE, 240, 1020, 540, 1520)])
save(v, os.path.join(OUT, "thumb-vertical.jpg"))
w = render(False, [("IF NEBULAS", ORANGE, 170, 1500, 960, 760), ("WERE CLOSER", WHITE, 130, 1500, 960, 930)])
save(w, os.path.join(OUT, "thumb.jpg"), (1280, 720))
