"""python lib/photosheet.py <code> out.jpg -> labelled contact sheet of photos/*.jpg and first frames of footage/*.mp4"""
import os, sys, glob, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import case_dir, FF
from PIL import Image, ImageDraw
d = case_dir(sys.argv[1]); items = []
for f in sorted(glob.glob(os.path.join(d, "photos", "*.jpg"))): items.append((os.path.basename(f)[:-4], Image.open(f).convert("RGB")))
for f in sorted(glob.glob(os.path.join(d, "footage", "*.mp4"))):
    for t in (5, 30):
        b = subprocess.run([FF, "-v", "error", "-ss", str(t), "-i", f, "-frames:v", "1", "-vf", "scale=480:-2", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
        if b:
            import io; items.append((f"VID {os.path.basename(f)[:-4]} @{t}s", Image.open(io.BytesIO(b)).convert("RGB")))
c = 6; tw, th = 320, 260
S = Image.new("RGB", (c * tw, ((len(items) + c - 1) // c) * th), (40, 40, 40)); dr = ImageDraw.Draw(S)
for i, (n, im) in enumerate(items):
    x, y = (i % c) * tw, (i // c) * th; sz = im.size; im.thumbnail((tw - 8, th - 30)); S.paste(im, (x + 4, y + 4))
    dr.text((x + 4, y + th - 22), f"{n} {sz[0]}x{sz[1]}", fill=(255, 230, 0))
S.save(sys.argv[2], quality=85); print(len(items), "items")
