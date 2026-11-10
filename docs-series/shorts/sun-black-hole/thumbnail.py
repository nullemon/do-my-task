"""Thumbnails: out/thumb.jpg (1280x720) and out/thumb-vertical.jpg (1080x1920).
The VFX black hole over the park at night, white "WHAT IF THE SUN" over big orange words (same font/style as the captions).
Usage: /home/user/ttsenv/bin/python thumbnail.py [t]   (t = video time of the background frame)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import short_vfx as V
import numpy as np
from PIL import Image
from lib.text import word_layer, composite, ORANGE

T = float(sys.argv[1]) if len(sys.argv) > 1 else 22.95    # full-size hole, just after the "6 KM" flare peak, before the frost
WHITE = (250, 250, 250)
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)


def save(img, path, size=None):
    im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
    if size: im = im.resize(size, Image.LANCZOS)
    im.save(path, quality=92); print(path, im.size)


def render(vertical, lines):
    sc = V.VFX(vertical)
    sc.overlay = lambda out, t, s: None                   # no captions / readouts
    img = sc.frame(T)
    for w, col, size, maxw, x, y in lines:
        rgba, _ = word_layer(w, size, maxw, fill=col)
        composite(img, rgba, x, y, 1.0)
    return img


# 9:16 (hole centred at (548, 585))
v = render(True, [("WHAT IF THE SUN", WHITE, 100, 1000, 540, 1060),
                  ("BECAME A", ORANGE, 170, 1000, 540, 1215),
                  ("BLACK", ORANGE, 250, 1020, 540, 1420),
                  ("HOLE?", ORANGE, 250, 1020, 540, 1650)])
save(v, os.path.join(OUT, "thumb-vertical.jpg"))

# 16:9 (rendered at 1920x1080, hole at (1230, 330)); text block bottom-left, under/left of the hole
w = render(False, [("WHAT IF THE SUN", WHITE, 92, 900, 620, 560),
                   ("BECAME A", ORANGE, 175, 1000, 620, 715),
                   ("BLACK HOLE?", ORANGE, 205, 1240, 700, 905)])
save(w, os.path.join(OUT, "thumb.jpg"), (1280, 720))
