"""Thumbnails: out/thumb-vertical.jpg (1080x1920) and out/thumb.jpg (1280x720, channel page; there is no 16:9 video).
TON 618 (seen from 8,000 au) filling the park sky, "IF TON 618 WAS OUR SUN" in the caption style.
Usage: /home/user/ttsenv/bin/python thumbnail.py [t]   (t = video time of the background frame; default: just after the pull-back)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import short as V
import numpy as np
from PIL import Image
from lib.text import word_layer, composite, ORANGE

T = float(sys.argv[1]) if len(sys.argv) > 1 else round(V.T_PULL1 + 0.5, 2)
WHITE = (250, 250, 250)
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)


def save(img, path, size=None):
    im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
    if size: im = im.resize(size, Image.LANCZOS)
    im.save(path, quality=92); print(path, im.size)


def render(sc, lines):
    img = sc.frame(T, overlay=False)
    for w, col, size, maxw, x, y in lines:
        rgba, _ = word_layer(w, size, maxw, fill=col)
        composite(img, rgba, x, y, 1.0)
    return img


v = render(V.Scene(True), [("IF", WHITE, 120, 1000, 540, 1010), ("TON 618", ORANGE, 230, 1020, 540, 1190),
                           ("WAS OUR", WHITE, 120, 1000, 540, 1370), ("SUN", ORANGE, 260, 1000, 540, 1570)])
save(v, os.path.join(OUT, "thumb-vertical.jpg"))
w = render(V.Scene(False, f_px=600.0, C=(1340.0, 330.0)),
           [("IF", WHITE, 100, 900, 430, 300), ("TON 618", ORANGE, 190, 820, 430, 480), ("WAS OUR SUN", ORANGE, 135, 820, 430, 680)])
save(w, os.path.join(OUT, "thumb.jpg"), (1280, 720))
