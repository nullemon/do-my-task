"""python lib/clipsheet.py video.mp4 out.jpg [n=36] [t0] [t1]  -> timestamped frame grid (for picking moments, spotting logos/subtitles)"""
import sys, os, subprocess, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import FF, probe_dur, probe_wh
from PIL import Image, ImageDraw
f, out = sys.argv[1], sys.argv[2]; n = int(sys.argv[3]) if len(sys.argv) > 3 else 36
T0 = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
L = probe_dur(f); W, H = probe_wh(f)
T1 = float(sys.argv[5]) if len(sys.argv) > 5 else L; cols = 6; tw = 320; th = int(H * tw / W)
S = Image.new("RGB", (cols * tw, ((n + cols - 1) // cols) * th)); d = ImageDraw.Draw(S)
for k in range(n):
    t = T0 + (T1 - T0) * (k + 0.5) / n
    b = subprocess.run([FF, "-v", "error", "-ss", f"{t:.2f}", "-i", f, "-frames:v", "1", "-vf", f"scale={tw}:{th}", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    if not b: continue
    x, y = (k % cols) * tw, (k // cols) * th; S.paste(Image.open(io.BytesIO(b)), (x, y))
    d.rectangle([x, y, x + 64, y + 18], fill=(0, 0, 0)); d.text((x + 3, y + 3), f"{t:.1f}s", fill=(255, 255, 0))
S.save(out, quality=82); print(f"{W}x{H} {L:.1f}s")
