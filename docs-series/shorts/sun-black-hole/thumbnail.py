"""out/thumb-vertical.jpg (1080x1920): the locked park frame at the Einstein-ring moment, frost and lamps on, 4 big words."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import short as S
import short_locked as B
import numpy as np
from PIL import Image
from lib.text import word_layer, composite, hud_text, ORANGE

sc = B.Locked(True)
sc.overlay = lambda out, t, s: None
sc.facts = lambda out, t: None
t = S.wt("scope", "BENDING")
st0 = sc.st
def st(tt):
    s = st0(tt); s["frost"] = 0.85; s["lamps"] = 1.0; s["night"] = 1.0; return s
sc.st = st
img = sc.frame(t)
for w, col, size, y in (("WHAT IF THE SUN", (245, 245, 245), 92, 930), ("BECAME A", (245, 245, 245), 92, 1035),
                        ("BLACK", ORANGE, 210, 1190), ("HOLE?", ORANGE, 210, 1385)):
    rgba, _ = word_layer(w, size, 1000, fill=col)
    composite(img, rgba, 540, y, 1.0)
hud_text(img, "ILLUSTRATION · BLACK HOLE ENLARGED", 540, 1490, 26, "SemiBold", (215, 225, 240), 0.9, 0.18)
os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(HERE, "out", "thumb-vertical.jpg"), quality=92)
print("ok")
