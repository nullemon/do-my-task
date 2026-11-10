"""Thumbnails: the valley under the night sky with glowing year labels + "EVERY STAR IS A DATE".
Usage: /home/user/ttsenv/bin/python thumbnail.py vert|wide  -> out/thumb-vertical.jpg (1080x1920) | out/thumb.jpg (1280x720)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import short as S
import numpy as np
from PIL import Image
from lib.text import word_layer, composite, ORANGE

vert = sys.argv[1] != "wide"
sc = S.Scene(vert)
W, H = sc.L.W, sc.L.H
T = 11.25                                         # Vega "2001" just popped, Arcturus "1989" still up, Milky Way core rising
# show three labels at once for the thumbnail: Arcturus, Vega (their real places at this sidereal time) + Andromeda
keep = {"arct", "vega"}
S.LABELS[:] = [lb if lb[0] not in keep else lb[:7] + (T - 2.0, T - 1.0, T + 5.0) for lb in S.LABELS]
caps = sc.caps.draw; sc.caps.draw = lambda out, t: None
_place = sc.label_place
def place(lb, x, y, rr):                          # thumbnail only: both labels hang below their stars (no overlap)
    ax, ay, side = _place(lb, x, y, rr)
    if lb[0] in keep:
        ay = y + (150 if vert else 120)
        side = 1 if x < W * (0.5 if lb[0] == "vega" else 0.85) else -1
        ax = x + side * 130
    return ax, ay, side
sc.label_place = place
img = sc.frame(T)
WHITE = (250, 250, 250)
if vert:
    for w, col, size, y in (("EVERY STAR", WHITE, 150, 1080), ("IS A", ORANGE, 150, 1230), ("DATE", ORANGE, 300, 1420)):
        rgba, _ = word_layer(w, size, 960, fill=col); composite(img, rgba, W / 2, y, 1.0)
    name = "thumb-vertical.jpg"
else:
    for w, col, size, x, y in (("EVERY STAR", WHITE, 120, 560, 560), ("IS A DATE", ORANGE, 175, 600, 740)):
        rgba, _ = word_layer(w, size, 1000, fill=col); composite(img, rgba, x, y, 1.0)
    name = "thumb.jpg"
im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
if not vert: im = im.resize((1280, 720), Image.LANCZOS)
im.save(os.path.join(HERE, "out", name), quality=92); print("ok", name, im.size)
