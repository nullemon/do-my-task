"""python lib/cliprows.py <code> out.jpg [cols=10]  -> one row per footage clip, frames evenly spaced, timestamps"""
import sys, os, subprocess, io, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import case_dir, FF, probe_dur
from PIL import Image, ImageDraw
d = case_dir(sys.argv[1]); cols = int(sys.argv[3]) if len(sys.argv) > 3 else 10; tw = 192
rows = []
for f in sorted(glob.glob(os.path.join(d, "footage", "*.mp4"))):
    L = probe_dur(f); ims = []
    for k in range(cols):
        t = L * (k + 0.5) / cols
        b = subprocess.run([FF, "-v", "error", "-ss", f"{t:.1f}", "-i", f, "-frames:v", "1", "-vf", f"scale={tw}:108:force_original_aspect_ratio=decrease,pad={tw}:108:-1:-1",
                            "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
        ims.append((t, Image.open(io.BytesIO(b)).convert("RGB") if b else Image.new("RGB", (tw, 108))))
    rows.append((os.path.basename(f)[:-4], L, ims))
S = Image.new("RGB", (cols * tw, len(rows) * 124), (25, 25, 25)); dr = ImageDraw.Draw(S)
for r, (n, L, ims) in enumerate(rows):
    y = r * 124; dr.text((2, y + 1), f"{n}  ({L:.0f}s)", fill=(255, 255, 255))
    for k, (t, im) in enumerate(ims):
        S.paste(im, (k * tw, y + 15)); dr.text((k * tw + 2, y + 15), f"{t:.0f}", fill=(255, 255, 0))
S.save(sys.argv[2], quality=80); print(len(rows), "clips")
