"""Thumbnails (pattern of ../other-suns/thumbnail.py): out/thumb.jpg (1280x720) and out/thumb-vertical.jpg (1080x1920).
The blazing supernova over the park, lawn lit blue-white with long shadows, "BETELGEUSE EXPLODES" in the caption style.
Usage: /home/user/ttsenv/bin/python thumbnail.py [t]   (t = video time of the background frame)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import short as V
import numpy as np
from PIL import Image
from lib.text import word_layer, composite, ORANGE

T = float(sys.argv[1]) if len(sys.argv) > 1 else 14.2
WHITE = (250, 250, 250)
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)


def save(img, path, size=None):
    im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
    if size: im = im.resize(size, Image.LANCZOS)
    im.save(path, quality=92); print(path, im.size)


def render(vertical, lines):
    sc = V.Scene(vertical)
    sc.overlay = lambda out, t: None                      # no captions / readouts
    img = sc.frame(T)
    for w, col, size, maxw, x, y in lines:
        rgba, _ = word_layer(w, size, maxw, fill=col)
        composite(img, rgba, x, y, 1.0)
    return img


v = render(True, [("BETELGEUSE", ORANGE, 190, 1000, 540, 1130), ("EXPLODES", WHITE, 175, 1000, 540, 1300),
                  ("IF IT EXPLODED TONIGHT", ORANGE, 74, 980, 540, 1450)])
save(v, os.path.join(OUT, "thumb-vertical.jpg"))
w = render(False, [("BETELGEUSE", ORANGE, 190, 1000, 520, 640), ("EXPLODES", WHITE, 170, 1000, 520, 810)])
save(w, os.path.join(OUT, "thumb.jpg"), (1280, 720))
