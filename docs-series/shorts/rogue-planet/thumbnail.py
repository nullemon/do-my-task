"""Thumbnails: out/thumb-vertical.jpg (1080x1920) and out/thumb.jpg (1280x720, a re-framed band of the same still).
The dark giant over the wet city street, lightning in its clouds; "A ROGUE PLANET IS COMING".
Usage: /home/user/ttsenv/bin/python thumbnail.py [t]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import short as V
import numpy as np
from PIL import Image
from lib.text import word_layer, composite, ORANGE

T = float(sys.argv[1]) if len(sys.argv) > 1 else None
WHITE = (250, 250, 250)
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)


def save(img, path):
    im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)); im.save(path, quality=92); print(path, im.size)


sc = V.Scene()
sc.overlay = lambda out, t, cur, t0: None
t = T if T is not None else V.wt("close_b", "HEAVE") - 0.5
img = sc.frame(t)
v = img.copy()
for w, col, size, x, y in [("WHAT IF A", WHITE, 120, 540, 230), ("ROGUE PLANET", ORANGE, 150, 540, 1300), ("PASSED US?", ORANGE, 170, 540, 1480)]:
    rgba, _ = word_layer(w, size, 1000, fill=col); composite(v, rgba, x, y, 1.0)
save(v, os.path.join(OUT, "thumb-vertical.jpg"))
crop = img[300:300 + 608, 0:1080]
im = Image.fromarray((np.clip(crop, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((1280, 720), Image.LANCZOS)
w = np.asarray(im).astype(np.float32) / 255
for t_, col, size, x, y in [("A ROGUE PLANET", ORANGE, 120, 640, 110), ("PASSED EARTH", WHITE, 110, 640, 630)]:
    rgba, _ = word_layer(t_, size, 1200, fill=col); composite(w, rgba, x, y, 1.0)
save(w, os.path.join(OUT, "thumb.jpg"))
