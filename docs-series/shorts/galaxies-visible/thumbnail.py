"""Thumbnails: out/thumb-vertical.jpg (1080x1920) and out/thumb.jpg (1280x720, a crop of a second vertical render).
Andromeda huge over the city, "THIS IS IN OUR SKY RIGHT NOW" in the caption style. (Thumbnail-only liberty: Andromeda is
drawn about 3x its true angular size here; the video itself keeps true sizes.)
Usage: /home/user/ttsenv/bin/python thumbnail.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import short as V
import numpy as np
from PIL import Image
from lib.text import word_layer, composite, ORANGE

T = 9.8                                             # inside the Andromeda scene, after the flash
WHITE = (250, 250, 250)
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)


def save(img, path, size=None):
    im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
    if size: im = im.resize(size, Image.LANCZOS)
    im.save(path, quality=92); print(path, im.size)


def render(x, y, scale):
    V.SC["m31"]["items"] = [("m31", x, y, 0)]; V.SC["m31"]["c"] = (x, y); V.SC["m31"]["moon"] = None
    sc = V.Scene(True)
    st = sc.state
    sc.state = lambda key, t, t0, t1: (scale, 0.0, 1.15, 0.0) if key == "m31" else st(key, t, t0, t1)
    sc.overlay = lambda out, t, cur, t0, t1: None   # no captions / readouts
    return sc.frame(T)


v = render(540.0, 560.0, 3.0)
for w, col, size, x, y in (("THIS IS IN", WHITE, 120, 540, 960), ("OUR SKY", ORANGE, 230, 540, 1130), ("RIGHT NOW", ORANGE, 200, 540, 1320)):
    rgba, _ = word_layer(w, size, 1020, fill=col); composite(v, rgba, x, y, 1.0)
save(v, os.path.join(OUT, "thumb-vertical.jpg"))

h = render(640.0, 1050.0, 2.4)[760:760 + 608]          # 1080 x 608 crop with the skyline at the bottom
for w, col, size, x, y in (("THIS IS IN OUR SKY", ORANGE, 112, 540, 95), ("RIGHT NOW", WHITE, 96, 290, 540)):
    rgba, _ = word_layer(w, size, 1040, fill=col); composite(h, rgba, x, y, 1.0)
save(h, os.path.join(OUT, "thumb.jpg"), (1280, 720))
