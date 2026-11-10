"""Thumbnails: the blacked-out city under a blazing Milky Way + "THEY CALLED 911".
Usage: /home/user/ttsenv/bin/python thumbnail.py vert|wide  -> out/thumb-vertical.jpg (1080x1920) | out/thumb.jpg (1280x720)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import short as S
import numpy as np
from PIL import Image
from lib.text import word_layer, composite, hud_text, ORANGE

vert = sys.argv[1] != "wide"
sc = S.Scene(vert)
sc.overlay = lambda out, t: None
sc.mw_canvas *= 1.25                                      # a touch more blaze for the thumbnail
t = S.LN["twist"]["start"] + 1.0
img = sc.frame(t)
W, H = sc.L.W, sc.L.H
if vert:
    for w, col, size, y in (("THEY CALLED", (245, 245, 245), 120, 760), ("911", ORANGE, 330, 980)):
        rgba, _ = word_layer(w, size, 1000, fill=col); composite(img, rgba, W / 2, y, 1.0)
    hud_text(img, "…ABOUT A STRANGE SILVER CLOUD", W / 2, 1150, 40, "Bold", (235, 240, 250), 1.0, 0.10)
    name = "thumb-vertical.jpg"; out = img
else:
    for w, col, size, x, y in (("THEY CALLED", (245, 245, 245), 118, 1380, 300), ("911", ORANGE, 300, 1380, 500)):
        rgba, _ = word_layer(w, size, 900, fill=col); composite(img, rgba, x, y, 1.0)
    name = "thumb.jpg"; out = img
im = Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8))
if not vert: im = im.resize((1280, 720), Image.LANCZOS)
im.save(os.path.join(HERE, "out", name), quality=92); print("ok", name)
