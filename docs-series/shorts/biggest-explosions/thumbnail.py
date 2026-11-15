"""Thumbnails: out/thumb.jpg (1280x720) and out/thumb-vertical.jpg (1080x1920).
The quasar 3C 273 blazing at the galactic centre over the relit city; "THE BIGGEST EXPLOSIONS" in the caption style.
Usage: /home/user/ttsenv/bin/python thumbnail.py [t]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import short as V
import numpy as np
from PIL import Image as I
from lib.text import word_layer, composite, ORANGE

T = float(sys.argv[1]) if len(sys.argv) > 1 else V.T_SW["qgc"] + 1.6
WHITE = (250, 250, 250)
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
sc = V.Scene(True)
sc.overlay = lambda out, t, st: None
img = sc.frame(T)


def save(im, path):
    im = I.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)); im.save(path, quality=92); print(path, im.size)


def rs(a, w, h): return np.asarray(I.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).resize((w, h), I.LANCZOS)).astype(np.float32) / 255


v = img.copy()
for w, col, size, maxw, x, y in [("THE BIGGEST", WHITE, 120, 1000, 540, 230), ("EXPLOSIONS", ORANGE, 170, 1020, 540, 390),
                                 ("SEEN FROM EARTH", WHITE, 90, 1000, 540, 1180)]:
    rgba, _ = word_layer(w, size, maxw, fill=col); composite(v, rgba, x, y, 1.0)
save(v, os.path.join(OUT, "thumb-vertical.jpg"))
W = np.zeros((720, 1280, 3), np.float32)
cy = int(sc.C[1]); y0 = max(0, min(1920 - 1000, cy - 400))
W[:, 560:] = rs(img[y0:y0 + 1000, 40:1040], 720, 720)
W[:, :560] = rs(img[1100:1820, 0:560], 560, 720) * 0.8
for w, col, size, maxw, x, y in [("THE BIGGEST", WHITE, 74, 520, 290, 200), ("EXPLOSIONS", ORANGE, 96, 540, 290, 350),
                                 ("FROM EARTH", WHITE, 70, 520, 290, 500)]:
    rgba, _ = word_layer(w, size, maxw, fill=col); composite(W, rgba, x, y, 1.0)
save(W, os.path.join(OUT, "thumb.jpg"))
