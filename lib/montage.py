"""python lib/montage.py out.jpg img1 img2 ...  (grid of stills, labelled)"""
import sys, os
from PIL import Image, ImageDraw
fs = sys.argv[2:]; ims = [Image.open(f) for f in fs]; w0, h0 = ims[0].size
tw = 360 if h0 > w0 else 640; th = int(h0 * tw / w0); c = 6 if h0 > w0 else 3
S = Image.new("RGB", (c * tw, ((len(ims) + c - 1) // c) * th), (60, 60, 60)); d = ImageDraw.Draw(S)
for i, (f, im) in enumerate(zip(fs, ims)):
    x, y = (i % c) * tw, (i // c) * th; S.paste(im.resize((tw, th)), (x, y)); d.rectangle([x, y, x + 120, y + 20], fill=(0, 0, 0)); d.text((x + 3, y + 3), os.path.basename(f)[6:-4], fill=(255, 255, 0))
S.save(sys.argv[1], quality=85)
