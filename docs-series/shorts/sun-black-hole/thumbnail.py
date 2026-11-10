"""out/thumb-vertical.jpg (1080x1920): the VFX black hole over the frosty park, with big words."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import short_vfx as V
import numpy as np
from PIL import Image
from lib.text import word_layer, composite, ORANGE

sc = V.VFX(True)
sc.overlay = lambda out, t, s: None                      # no captions / readouts
img = sc.frame(V.T_COLD + 3.6)                            # hole + frost
for w, col, size, y in (("WHAT IF THE SUN", (250, 250, 250), 92, 1080), ("BECAME A", (250, 250, 250), 92, 1185),
                        ("BLACK", ORANGE, 220, 1350), ("HOLE?", ORANGE, 220, 1560)):
    rgba, _ = word_layer(w, size, 1000, fill=col)
    composite(img, rgba, 540, y, 1.0)
os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(HERE, "out", "thumb-vertical.jpg"), quality=92)
print("ok")
