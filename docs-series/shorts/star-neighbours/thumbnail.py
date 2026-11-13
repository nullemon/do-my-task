"""Thumbnails: out/thumb-vertical.jpg (1080x1920) and out/thumb.jpg (1280x720, centre crop of the vertical frame re-laid).
A blinding star (Eta Carinae's 1843 eruption at Alpha Centauri's distance) over the city, "IF THIS STAR WAS OUR NEIGHBOUR".
Usage: /home/user/ttsenv/bin/python thumbnail.py [t]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import short as V
import numpy as np
from PIL import Image
from lib.text import word_layer, composite, ORANGE

T = float(sys.argv[1]) if len(sys.argv) > 1 else 32.2
WHITE = (250, 250, 250)
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)


def save(img, path):
    im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)); im.save(path, quality=92); print(path, im.size); return im


sc = V.Scene(True)
sc.overlay = lambda out, t, st: None                       # no captions / readouts
base = sc.frame(T)
v = base.copy()
for w, col, size, y in (("IF THIS STAR", WHITE, 150, 1010), ("WAS OUR", WHITE, 150, 1170), ("NEIGHBOUR", ORANGE, 210, 1360)):
    rgba, _ = word_layer(w, size, 1020, fill=col); composite(v, rgba, 540, y, 1.0)
save(v, os.path.join(OUT, "thumb-vertical.jpg"))
# 16:9: the sky band with the star on the left, the city's skyline at the bottom, text on the right
crop = base[380:380 + 1080 * 9 // 16 * 2 // 2 + 0, :, :]
h = 1080 * 9 // 16                                         # 607 rows of the 1080-wide frame
crop = base[1460 - h:1460, :, :]
im = Image.fromarray((np.clip(crop, 0, 1) * 255).astype(np.uint8)).resize((1280, 720), Image.LANCZOS)
w = np.asarray(im).astype(np.float32) / 255
for txt, col, size, x, y in (("IF THIS STAR", WHITE, 92, 860, 250), ("WAS OUR", WHITE, 92, 860, 360), ("NEIGHBOUR", ORANGE, 118, 860, 490)):
    rgba, _ = word_layer(txt, size, 760, fill=col); composite(w, rgba, x, y, 1.0)
save(w, os.path.join(OUT, "thumb.jpg"))
