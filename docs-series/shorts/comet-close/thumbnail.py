"""Thumbnails: out/thumb-vertical.jpg (1080x1920) and out/thumb.jpg (1280x720, centre crop of a re-framed still).
Hale-Bopp's huge green coma with blue ion + white dust tails over the night park; "IF A COMET CAME THIS CLOSE".
Usage: /home/user/ttsenv/bin/python thumbnail.py [t]   (t = video time of the background frame)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import short as V
import numpy as np
from PIL import Image
from lib.text import word_layer, composite, ORANGE

T = float(sys.argv[1]) if len(sys.argv) > 1 else 17.2
WHITE = (250, 250, 250)
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)


def save(img, path):
    im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)); im.save(path, quality=92); print(path, im.size); return im


sc = V.Scene()
sc.overlay = lambda out, t, cur, t0: None                      # no captions / readouts
img = sc.frame(T)
v = img.copy()
for w, col, size, x, y in [("IF A COMET", WHITE, 130, 540, 1040), ("CAME THIS", ORANGE, 190, 540, 1210), ("CLOSE", ORANGE, 260, 540, 1420)]:
    rgba, _ = word_layer(w, size, 1000, fill=col); composite(v, rgba, x, y, 1.0)
save(v, os.path.join(OUT, "thumb-vertical.jpg"))
# 16:9: the sky half of the frame (head + tails) scaled into 1280x720, text on the right
crop = img[220:220 + 608, 0:1080]
im = Image.fromarray((np.clip(crop, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((1280, 720), Image.LANCZOS)
w = np.asarray(im).astype(np.float32) / 255
for t_, col, size, x, y in [("IF A COMET", WHITE, 92, 330, 470), ("CAME THIS CLOSE", ORANGE, 110, 640, 600)]:
    rgba, _ = word_layer(t_, size, 1200, fill=col); composite(w, rgba, x, y, 1.0)
save(w, os.path.join(OUT, "thumb.jpg"))
