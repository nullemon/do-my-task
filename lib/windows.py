"""python lib/windows.py video.mp4 out.jpg t1 t2 t3 ...  -> for each centre time, 8 frames at 1.5 s steps (t-5 .. t+5.5)"""
import sys, os, subprocess, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import FF, probe_wh
from PIL import Image, ImageDraw
f, out = sys.argv[1], sys.argv[2]; ts = [float(x) for x in sys.argv[3:]]
W, H = probe_wh(f); tw = 240; th = int(H * tw / W); cols = 8
S = Image.new("RGB", (cols * tw, len(ts) * th)); d = ImageDraw.Draw(S)
for r, c in enumerate(ts):
    for k in range(cols):
        t = max(0, c - 5 + 1.5 * k)
        b = subprocess.run([FF, "-v", "error", "-ss", f"{t:.2f}", "-i", f, "-frames:v", "1", "-vf", f"scale={tw}:{th}", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
        if b: S.paste(Image.open(io.BytesIO(b)), (k * tw, r * th))
        d.rectangle([k * tw, r * th, k * tw + 54, r * th + 16], fill=(0, 0, 0)); d.text((k * tw + 2, r * th + 2), f"{t:.1f}", fill=(255, 255, 0))
S.save(out, quality=80)
