"""Thumbnails: out/thumb.jpg (1280x720) and out/thumb-vertical.jpg (1080x1920).
The fireball plume over the park under a red-hot sky full of ejecta meteors, "THE DINOSAUR KILLER" in the caption style.
Usage: /home/user/ttsenv/bin/python thumbnail.py [t]   (t = video time of the background frame)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import short as V
import numpy as np
from PIL import Image
from lib.text import word_layer, composite, ORANGE

T = float(sys.argv[1]) if len(sys.argv) > 1 else 23.6
WHITE = (250, 250, 250)
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)


def save(img, path, size=None):
    im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
    if size: im = im.resize(size, Image.LANCZOS)
    im.save(path, quality=92); print(path, im.size)


def render(vertical, lines):
    sc = V.Scene(vertical)
    sc.overlay = lambda out, t: None                      # no captions / readouts / counter
    img = sc.frame(T)
    for w, col, size, maxw, x, y in lines:
        rgba, _ = word_layer(w, size, maxw, fill=col)
        composite(img, rgba, x, y, 1.0)
    return img


v = render(True, [("THE", WHITE, 120, 1000, 540, 1180), ("DINOSAUR", ORANGE, 230, 1020, 540, 1360),
                  ("KILLER", ORANGE, 260, 1000, 540, 1570), ("SEEN FROM THE GROUND", WHITE, 92, 1000, 540, 1760)])
save(v, os.path.join(OUT, "thumb-vertical.jpg"))
w = render(False, [("THE DINOSAUR", ORANGE, 170, 1000, 560, 640), ("KILLER", ORANGE, 210, 1000, 560, 820),
                   ("SEEN FROM THE GROUND", WHITE, 70, 900, 560, 975)])
save(w, os.path.join(OUT, "thumb.jpg"), (1280, 720))
