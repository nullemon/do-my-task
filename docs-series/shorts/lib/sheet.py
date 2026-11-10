"""contact sheet: python sheet.py out.jpg cols thumb_w img1 img2 ..."""
import sys, os
sys.path.insert(0, "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/shorts-common/pylib")
from PIL import Image, ImageDraw
out, cols, tw = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); fs = sys.argv[4:]
ims = [Image.open(f).convert("RGB") for f in fs]
th = int(tw * ims[0].height / ims[0].width); rows = (len(ims) + cols - 1) // cols
sh = Image.new("RGB", (tw * cols, th * rows), (20, 20, 20)); d = ImageDraw.Draw(sh)
for i, (f, im) in enumerate(zip(fs, ims)):
    x, y = (i % cols) * tw, (i // cols) * th; sh.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
    d.text((x + 6, y + 4), os.path.basename(f), fill=(255, 255, 0))
sh.save(out, quality=88)
