import sys, subprocess, re, json, os
d = sys.argv[1]; out = {}
for f in sorted(os.listdir(f"{d}/cl")):
    if not f.endswith(".mp4") or os.path.islink(f"{d}/cl/{f}"): continue
    r = subprocess.run(["ffmpeg","-i",f"{d}/cl/{f}","-vf","scale=160:90,select='gt(scene,0.28)',showinfo","-an","-f","null","-"],capture_output=True,text=True).stderr
    out[f[:-4]] = [round(float(x),1) for x in re.findall(r"pts_time:([\d.]+)", r)]
json.dump(out, open(f"{d}/cuts.json","w"))
for k,v in out.items(): print(k, v[:120])
