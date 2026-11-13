"""Thumbnails: a blazing star-filled sky (Omega Centauri / galactic-centre look) over the valley + "IF WE LIVED IN A STAR
CLUSTER". Usage: /home/user/ttsenv/bin/python thumbnail.py vert|wide -> out/thumb-vertical.jpg (1080x1920) |
out/thumb.jpg (1280x720, cropped from the vertical frame: there is no 16:9 video)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import short as S
import numpy as np
from PIL import Image
from lib.text import word_layer, composite, ORANGE

vert = sys.argv[1] != "wide"
sc = S.Scene(True)
sc.caps.draw = lambda out, t: None
sc.overlay = lambda out, t, cur, t0: None
T = 29.6                                           # galactic centre, settled
img = sc.frame(T)
W, H = 1080, 1920
WHITE = (250, 250, 250)
if vert:
    for w, col, size, y in (("IF WE LIVED", WHITE, 140, 1040), ("IN A STAR", WHITE, 140, 1185), ("CLUSTER", ORANGE, 230, 1370)):
        rgba, _ = word_layer(w, size, 980, fill=col); composite(img, rgba, W / 2, y, 1.0)
    im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)); name = "thumb-vertical.jpg"
else:
    crop = img[380:380 + 608]                       # 1080 x 608 band: sky core + treetops
    crop = crop.copy()
    for w, col, size, y in (("IF WE LIVED IN A", WHITE, 92, 400), ("STAR CLUSTER", ORANGE, 128, 520)):
        rgba, _ = word_layer(w, size, 1040, fill=col); composite(crop, rgba, W / 2, y, 1.0)
    im = Image.fromarray((np.clip(crop, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((1280, 720), Image.LANCZOS); name = "thumb.jpg"
im.save(os.path.join(HERE, "out", name), quality=92); print("ok", name, im.size)
