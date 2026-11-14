"""REDO v3 segmented renderer: renders a Short's frames in chunks (SCR/segs/seg_NNN.mp4, skipped if already complete),
then concatenates them into SCR/video_vert.mp4. A container restart loses at most one chunk.
Run (from anywhere, under nice):  /home/user/ttsenv/bin/python lib/render_v3.py <short_dir> [chunk_frames=150]
The Short's short.py must expose SCR, DUR, FPS and Scene(True).frame(t)."""
import os, sys, time, subprocess, importlib
d = os.path.abspath(sys.argv[1]); chunk = int(sys.argv[2]) if len(sys.argv) > 2 else 150
sys.path[:0] = [os.path.dirname(d), d, os.path.join(d, "audio")]
S = importlib.import_module("short")
from lib.post import Encoder

seg_dir = os.path.join(S.SCR, "segs"); os.makedirs(seg_dir, exist_ok=True)
n = int(round(S.DUR * S.FPS)); segs = [(a, min(a + chunk, n)) for a in range(0, n, chunk)]


def nframes(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries", "stream=nb_read_packets",
                        "-of", "csv=p=0", p], capture_output=True, text=True)
    try: return int(r.stdout.strip())
    except ValueError: return -1


sc = None; T0 = time.time()
for k, (a, b) in enumerate(segs):
    p = os.path.join(seg_dir, f"seg_{k:03d}.mp4")
    if os.path.exists(p) and nframes(p) == b - a: continue
    if sc is None: sc = S.Scene(True)
    tmp = p.replace(".mp4", ".part.mp4")
    enc = Encoder(tmp, sc.L.W, sc.L.H, S.FPS, crf=16)
    for i in range(a, b): enc.write(sc.frame(i / S.FPS))
    enc.close(); os.replace(tmp, p)
    print(f"seg {k + 1}/{len(segs)} frames {a}-{b} done  {time.time() - T0:.0f}s", flush=True)
lst = os.path.join(seg_dir, "list.txt")
with open(lst, "w") as f:
    for k in range(len(segs)): f.write(f"file 'seg_{k:03d}.mp4'\n")
out = os.path.join(S.SCR, "video_vert.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", out], check=True)
print("video", out, "frames", nframes(out), "expected", n, flush=True)
