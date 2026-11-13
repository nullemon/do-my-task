"""python lib/sheets.py <video.mp4>  -> <video>_strip8.jpg (8 frames) + <video>_sheet.jpg (1 frame every 4.5 s, timestamped)"""
import os, sys, subprocess, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import FF, probe_dur, probe_wh, font, MXB
from PIL import Image, ImageDraw
f = sys.argv[1]; D = probe_dur(f); W, H = probe_wh(f); pre = f.rsplit(".", 1)[0]
def grab(t, w):
    h = int(H * w / W) // 2 * 2
    b = subprocess.run([FF, "-v", "error", "-ss", f"{t:.2f}", "-i", f, "-frames:v", "1", "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return Image.frombytes("RGB", (w, h), b) if len(b) == w * h * 3 else Image.new("RGB", (w, h))
tw = 300 if H > W else 480
ims = [grab(D * (i + 0.5) / 8, tw) for i in range(8)]
S = Image.new("RGB", (tw * 8, ims[0].height)); [S.paste(im, (i * tw, 0)) for i, im in enumerate(ims)]
S.save(pre + "_strip8.jpg", quality=85)
tw = 216 if H > W else 384; ts = [x * 4.5 for x in range(int(D / 4.5) + 1)]
c = 12 if H > W else 8; ims = [grab(t, tw) for t in ts]; th = ims[0].height
S = Image.new("RGB", (c * tw, ((len(ims) + c - 1) // c) * th)); d = ImageDraw.Draw(S)
for i, (t, im) in enumerate(zip(ts, ims)):
    x, y = (i % c) * tw, (i // c) * th; S.paste(im, (x, y))
    d.rectangle([x, y, x + 74, y + 24], fill=(0, 0, 0)); d.text((x + 4, y + 2), f"{int(t//60)}:{int(t%60):02d}", font=font(MXB, 18), fill=(255, 220, 0))
S.save(pre + "_sheet.jpg", quality=82); print("wrote", pre + "_strip8.jpg", pre + "_sheet.jpg")
