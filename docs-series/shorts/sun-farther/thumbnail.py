"""Thumbnails: out/thumb.jpg (1280x720) and out/thumb-vertical.jpg (1080x1920).
The frozen village under a starry sky at Neptune's distance, the Sun a brilliant star, snow of frozen air falling;
"IF EARTH DRIFTED AWAY" in the caption style.
Usage: /home/user/ttsenv/bin/python thumbnail.py [t]   (t = video time of the background frame)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import short as V
import numpy as np
from PIL import Image as I
from lib.text import word_layer, composite, ORANGE

T = float(sys.argv[1]) if len(sys.argv) > 1 else 34.5
WHITE = (250, 250, 250)
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
sc = V.Scene()
sc.overlay = lambda out, t, cur, t0: None
sc.today_ring = lambda out, t, a: None
img = sc.frame(T)


def save(im, path):
    im = I.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)); im.save(path, quality=92); print(path, im.size)


def rs(a, w, h): return np.asarray(I.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).resize((w, h), I.LANCZOS)).astype(np.float32) / 255


v = img.copy()
for w, col, size, maxw, x, y in [("IF EARTH", WHITE, 130, 1000, 540, 260), ("DRIFTED", ORANGE, 220, 1020, 540, 440), ("AWAY", ORANGE, 240, 1020, 540, 640)]:
    rgba, _ = word_layer(w, size, maxw, fill=col); composite(v, rgba, x, y, 1.0)
save(v, os.path.join(OUT, "thumb-vertical.jpg"))
W = np.zeros((720, 1280, 3), np.float32)
W[:, 560:] = rs(img[880:1600], 720, 720)
W[:, :560] = rs(img[300:1100, :], 560, 720) * 0.85
for w, col, size, maxw, x, y in [("IF EARTH", WHITE, 84, 520, 290, 200), ("DRIFTED", ORANGE, 130, 540, 290, 350), ("AWAY", ORANGE, 150, 540, 290, 510)]:
    rgba, _ = word_layer(w, size, maxw, fill=col); composite(W, rgba, x, y, 1.0)
save(W, os.path.join(OUT, "thumb.jpg"))
