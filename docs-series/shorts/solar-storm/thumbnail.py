"""Thumbnails: the dark city under massive red and green auroras + "THE 1859 STORM / IF IT HIT TODAY".
Usage: /home/user/ttsenv/bin/python thumbnail.py vert|wide  -> out/thumb-vertical.jpg (1080x1920) | out/thumb.jpg (1280x720)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import short as S
import numpy as np
from PIL import Image
from lib.text import word_layer, composite, ORANGE

vert = sys.argv[1] != "wide"
sc = S.Scene(vert)
sc.overlay = lambda out, t: None
t = S.LN["cost"]["start"] + 1.2                      # blackout, aurora blazing, emergency lights
img = sc.frame(t)
W, H = sc.L.W, sc.L.H
if vert:
    for w, col, size, y in (("THE 1859 STORM", (245, 245, 245), 118, 900), ("IF IT HIT TODAY", ORANGE, 150, 1060)):
        rgba, _ = word_layer(w, size, 1000, fill=col); composite(img, rgba, W / 2, y, 1.0)
    im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)); name = "thumb-vertical.jpg"
else:
    for w, col, size, y in (("THE 1859 STORM", (245, 245, 245), 120, 560), ("IF IT HIT TODAY", ORANGE, 150, 720)):
        rgba, _ = word_layer(w, size, 1500, fill=col); composite(img, rgba, W / 2, y, 1.0)
    im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((1280, 720), Image.LANCZOS); name = "thumb.jpg"
im.save(os.path.join(HERE, "out", name), quality=92); print("ok", name)
