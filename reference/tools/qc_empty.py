"""qc_empty.py video.mp4 [out_prefix]
Samples a frame every 2 s, splits it into a 6x10 grid, and counts 'empty' cells
(nearly flat: luminance std < 8, or very blurry: Laplacian variance < 12).
Flags frames with > 40% empty cells (> 25% in the first 30 s).
Writes <out_prefix>_first30.jpg (1 fps contact sheet of the first 30 s) and prints a report."""
import sys, subprocess, json, numpy as np
from PIL import Image
f = sys.argv[1]; pre = sys.argv[2] if len(sys.argv) > 2 else f.rsplit(".", 1)[0] + "_qc"
info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
       "stream=width,height:format=duration", "-of", "json", f], capture_output=True, text=True).stdout)
W, H = info["streams"][0]["width"], info["streams"][0]["height"]; dur = float(info["format"]["duration"])
w, h = W // 4, H // 4
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", f, "-vf", f"fps=1/2,scale={w}:{h},format=gray", "-f", "rawvideo", "-"],
                     capture_output=True).stdout
n = len(raw) // (w * h); flags = []; scores = []
rows, cols = (10, 6) if H > W else (6, 10)
for i in range(n):
    a = np.frombuffer(raw[i * w * h:(i + 1) * w * h], np.uint8).reshape(h, w).astype(float)
    lap = np.abs(a[1:-1, 1:-1] * 4 - a[:-2, 1:-1] - a[2:, 1:-1] - a[1:-1, :-2] - a[1:-1, 2:])
    empty = 0
    for r in range(rows):
        for c in range(cols):
            ys, ye = r * h // rows, (r + 1) * h // rows; xs, xe = c * w // cols, (c + 1) * w // cols
            cell = a[ys:ye, xs:xe]; lc = lap[max(0, ys - 1):max(1, ye - 1), max(0, xs - 1):max(1, xe - 1)]
            if cell.std() < 8 or (lc ** 2).mean() < 12: empty += 1
    frac = empty / (rows * cols); t = i * 2; scores.append(frac)
    lim = 0.25 if t < 30 else 0.40
    if frac > lim: flags.append((t, frac))
print(f"{f}: {n} frames checked, mean empty {np.mean(scores):.0%}, flagged {len(flags)} ({len(flags)/max(1,n):.0%})")
for t, fr in flags[:40]: print(f"  FLAG {int(t//60)}:{int(t%60):02d}  {fr:.0%} empty")
tw, th = (216, 384) if H > W else (384, 216)
raw = subprocess.run(["ffmpeg", "-v", "error", "-t", "30", "-i", f, "-vf", f"fps=1,scale={tw}:{th}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                     capture_output=True).stdout
k = len(raw) // (tw * th * 3); c = 10 if H > W else 6; S = Image.new("RGB", (c * tw, ((k + c - 1) // c) * th))
for i in range(k): S.paste(Image.frombytes("RGB", (tw, th), raw[i * tw * th * 3:(i + 1) * tw * th * 3]), ((i % c) * tw, (i // c) * th))
S.save(pre + "_first30.jpg", quality=85); print("contact sheet:", pre + "_first30.jpg")
