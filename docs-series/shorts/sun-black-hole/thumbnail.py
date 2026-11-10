"""out/thumb-vertical.jpg (1080x1920): the frozen night park, the telescope view with the lensed ring, 4 big words."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import short as S
import numpy as np
from PIL import Image
from lib.text import word_layer, composite, hud_text, ORANGE

sc = S.Scene(True)
sc.overlay = lambda out, t, s: None                      # no captions / HUD
t = S.T_SC0 + 0.78 * (S.T_SC1 - S.T_SC0)                 # galaxy close to alignment: ring
st0 = sc.st
def st(tt):
    s = st0(tt); s["frost"] = 0.9; s["inset"] = 1.0; s["lamps"] = 1.0; s["night"] = 1.0; s["zoom"] = 1.0; return s
sc.st = st
img = sc.frame(t)
for i, (w, col, size, y) in enumerate((("WHAT IF THE SUN", (245, 245, 245), 96, 1020), ("BECAME A", (245, 245, 245), 96, 1130),
                                       ("BLACK", ORANGE, 200, 1290), ("HOLE?", ORANGE, 200, 1480))):
    rgba, _ = word_layer(w, size, 1000, fill=col)
    composite(img, rgba, 540, y, 1.0)
os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(HERE, "out", "thumb-vertical.jpg"), quality=92)
print("ok")
