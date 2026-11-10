"""Thumbnails: the broken Big Dipper with its star trails over the night park + "YOUR SKY IN 1 MILLION YEARS".
Usage: /home/user/ttsenv/bin/python thumbnail.py vert|wide  -> out/thumb-vertical.jpg (1080x1920) | out/thumb.jpg (1280x720)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import short as S
import numpy as np
from PIL import Image
from lib.text import word_layer, composite, ORANGE

vert = sys.argv[1] != "wide"
T = S.T_BROKEN - 0.30                                   # Dipper stretched to the limit, trails + tension colours, before the snap
sc = S.Scene(vert)
_fx = sc.feature_fx
def fx_no_labels(fx, t):                                # keep the graphics, drop the small readouts
    _fx(fx, t); return []
sc.feature_fx = fx_no_labels
sc.caps.draw = lambda out, t: None
_ov = sc.overlay
sc.overlay = lambda out, t, E, jobs: None               # no counter / captions: the title is the text
img = sc.frame(T)
WHITE = (250, 250, 250)
if vert:
    for w, col, size, y in (("YOUR SKY IN", WHITE, 130, 330), ("1 MILLION", ORANGE, 210, 540), ("YEARS", ORANGE, 210, 750)):
        rgba, _ = word_layer(w, size, 980, fill=col); composite(img, rgba, sc.L.W / 2, y, 1.0)
    name = "thumb-vertical.jpg"
else:
    for w, col, size, x, y in (("YOUR SKY IN", WHITE, 120, 560, 190), ("1 MILLION YEARS", ORANGE, 150, 640, 370)):
        rgba, _ = word_layer(w, size, 1150, fill=col); composite(img, rgba, x, y, 1.0)
    name = "thumb.jpg"
im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
if not vert: im = im.resize((1280, 720), Image.LANCZOS)
im.save(os.path.join(HERE, "out", name), quality=92); print("ok", name, im.size)
