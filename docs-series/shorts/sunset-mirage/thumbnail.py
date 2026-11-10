"""Thumbnails: out/thumb.jpg (1280x720) and out/thumb-vertical.jpg (1080x1920).
The Sun touching the ridge, the glowing dashed "REAL SUN" ghost below the horizon in the X-ray cutaway,
"THIS SUNSET IS FAKE" / "IT'S ALREADY GONE" in the caption style.
Usage: /home/user/ttsenv/bin/python thumbnail.py [t]   (t = video time of the background frame)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import short as V
import numpy as np
from PIL import Image
from lib.text import word_layer, composite, hud_text, ORANGE

T = float(sys.argv[1]) if len(sys.argv) > 1 else 6.4
WHITE = (250, 250, 250); CYAN = (140, 235, 255)
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)


def save(img, path, size=None):
    im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
    if size: im = im.resize(size, Image.LANCZOS)
    im.save(path, quality=92); print(path, im.size)


def render(vertical, lines, lab_size):
    sc = V.Scene(vertical)
    def ov(out, t, s):                                   # no captions / readouts; a bold "REAL SUN" label on the ghost
        gx, gy = sc.ghost_xy(s)
        hud_text(out, "REAL SUN", gx + sc.R + lab_size * 3.3, gy - 4, lab_size, "Black", CYAN, 1.0, 0.08, display=True)
        hud_text(out, "WHAT YOU SEE", sc.sx - sc.R - lab_size * 4.6, sc.ypx(s["app_c"]) - 4, int(lab_size * 0.8), "Black", (255, 205, 110), 1.0, 0.08, display=True)
    sc.overlay = ov
    img = sc.frame(T)
    for w, col, size, maxw, x, y in lines:
        rgba, _ = word_layer(w, size, maxw, fill=col)
        composite(img, rgba, x, y, 1.0)
    return img


v = render(True, [("THIS SUNSET", WHITE, 150, 1000, 540, 420), ("IS FAKE", ORANGE, 230, 1020, 540, 610),
                  ("IT'S ALREADY GONE", ORANGE, 110, 1000, 540, 1000)], 44)
save(v, os.path.join(OUT, "thumb-vertical.jpg"))
w = render(False, [("THIS SUNSET", WHITE, 120, 900, 560, 200), ("IS FAKE", ORANGE, 190, 900, 560, 380),
                   ("IT'S ALREADY GONE", ORANGE, 80, 900, 560, 560)], 40)
save(w, os.path.join(OUT, "thumb.jpg"), (1280, 720))
