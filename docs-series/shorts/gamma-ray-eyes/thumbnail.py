"""Thumbnails: the blazing gamma-ray Moon over the park + "GAMMA RAY EYES" / "THE MOON OUTSHINES THE SUN".
Usage: /home/user/ttsenv/bin/python thumbnail.py vert|wide  -> out/thumb-vertical.jpg (1080x1920) | out/thumb.jpg (1280x720)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import short as S
import numpy as np
from PIL import Image
from lib.text import word_layer, composite, hud_text, ORANGE

vert = sys.argv[1] != "wide"
sc = S.Scene(vert)
sc.overlay = lambda out, t: None
t = S.T_BLAZE + 0.9                       # shock ring gone, orb at full blaze
img = sc.frame(t)
W, H = sc.L.W, sc.L.H
if vert:
    for w, col, size, y in (("GAMMA RAY EYES", (215, 150, 255), 120, 1040), ("THE MOON", (245, 245, 250), 150, 1215), ("OUTSHINES THE SUN", ORANGE, 118, 1370)):
        rgba, _ = word_layer(w, size, 1000, fill=col); composite(img, rgba, W / 2, y, 1.0)
    name = "thumb-vertical.jpg"
else:
    for w, col, size, x, y in (("GAMMA RAY EYES", (215, 150, 255), 100, 560, 640), ("THE MOON OUTSHINES", (245, 245, 250), 92, 560, 790),
                               ("THE SUN", ORANGE, 150, 560, 930)):
        rgba, _ = word_layer(w, size, 1000, fill=col); composite(img, rgba, x, y, 1.0)
    name = "thumb.jpg"
im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
if not vert: im = im.resize((1280, 720), Image.LANCZOS)
im.save(os.path.join(HERE, "out", name), quality=92); print("ok", name, im.size)
