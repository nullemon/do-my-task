"""python lib/build.py <code> V|H [preview_seconds]  -> concat span files + mux audio -> cases/<code>/deliver/*.mp4"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_case, FF, probe_dur
code, fmt = sys.argv[1], sys.argv[2].upper(); pv = float(sys.argv[3]) if len(sys.argv) > 3 else None
cfg, scr = load_case(code); W = cfg.WORK
tl = json.load(open(os.path.join(W, "timeline.json"), encoding="utf-8"))
out = os.path.join(W, f"out_{fmt}"); spans = tl["spans"]
idx = [i for i in range(len(spans)) if pv is None or spans[i]["t0"] < pv]
miss = [i for i in idx if not os.path.exists(os.path.join(out, f"s{i:03d}.mp4"))]
if miss: raise SystemExit(f"missing spans: {miss}")
lst = os.path.join(out, "concat.txt")
open(lst, "w").write("".join(f"file 's{i:03d}.mp4'\n" for i in idx))
vid = os.path.join(out, "video.mp4")
subprocess.run([FF, "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", vid], check=True)
dl = os.path.join(cfg.DIR, "deliver"); os.makedirs(dl, exist_ok=True)
name = (f"{cfg.DOG} - {cfg.HOOK_TITLE} (9x16)" if fmt == "V" else f"16x9 - {cfg.DOG} - {cfg.HOOK_TITLE}")
if pv: name = f"PREVIEW {int(pv)}s - " + name
dst = os.path.join(dl, name + ".mp4")
cmd = [FF, "-loglevel", "error", "-y", "-i", vid, "-i", os.path.join(W, "mix.m4a"), "-map", "0:v", "-map", "1:a", "-c:v", "copy"]
cmd += (["-c:a", "aac", "-b:a", "192k", "-t", f"{pv:.3f}", "-af", f"afade=t=out:st={pv-0.6:.2f}:d=0.6"] if pv else ["-c:a", "copy", "-shortest"])
cmd += ["-movflags", "+faststart", dst]
subprocess.run(cmd, check=True)
print("wrote", dst, f"{probe_dur(dst):.1f}s")
