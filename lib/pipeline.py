"""One entry point for the launchers:
  python lib/pipeline.py <code> voice      TTS + timeline + music/mix
  python lib/pipeline.py <code> preview    first 30 s in both formats (+ stills + empty-screen QC)
  python lib/pipeline.py <code> render     full render 9:16 then 16:9 (resumable: RESUME is always on)
  python lib/pipeline.py <code> qc         qc_empty + strip + contact sheet + loudness for the delivered files
  python lib/pipeline.py <code> new "<Dog Name>"
"""
import os, sys, subprocess, glob, shutil
os.environ.pop("SSLKEYLOGFILE", None)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, LIB, FF
PY = sys.executable
def run(*a, env=None):
    e = dict(os.environ); e.update(env or {})
    print(">>", " ".join(a), flush=True); subprocess.run([PY, *a], check=True, env=e, cwd=ROOT)

def voice(code):
    run(os.path.join(LIB, "tts.py"), code); run(os.path.join(LIB, "timeline.py"), code); run(os.path.join(LIB, "mix.py"), code)

def preview(code, secs=30):
    for f in ("V", "H"):
        run(os.path.join(LIB, "render.py"), code, f, env={"PREVIEW": str(secs), "RESUME": "1"})
        run(os.path.join(LIB, "build.py"), code, f, str(secs))
    qc(code, preview=True)

def render(code):
    for f in ("V", "H"):
        run(os.path.join(LIB, "render.py"), code, f, env={"RESUME": "1"})
        run(os.path.join(LIB, "build.py"), code, f)

def qc(code, preview=False):
    d = os.path.join(ROOT, "cases", code, "deliver")
    for v in sorted(glob.glob(os.path.join(d, "*.mp4"))):
        if ("PREVIEW" in os.path.basename(v)) != preview: continue
        qd = os.path.join(d, "qc"); os.makedirs(qd, exist_ok=True)
        pre = os.path.join(qd, os.path.basename(v)[:-4])
        run(os.path.join(LIB, "qc_empty.py"), v, pre)
        if not preview:
            run(os.path.join(LIB, "sheets.py"), v)
            for x in glob.glob(v[:-4] + "_*.jpg"): shutil.move(x, os.path.join(qd, os.path.basename(x)))
        r = subprocess.run([FF, "-hide_banner", "-i", v, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
        tail = r[r.rfind("Summary:"):]
        I = [l for l in tail.splitlines() if l.strip().startswith(("I:", "Peak:"))]
        print("   loudness", " | ".join(x.strip() for x in I))

def new(code, name):
    d = os.path.join(ROOT, "cases", code)
    for sub in ("footage", "photos", "work", "deliver"): os.makedirs(os.path.join(d, sub), exist_ok=True)
    tpl = os.path.join(ROOT, "cases", "hachiko")
    for f in ("cfg.py", "script.py"):
        dst = os.path.join(d, f)
        if not os.path.exists(dst):
            s = open(os.path.join(tpl, f), encoding="utf-8").read()
            open(dst, "w", encoding="utf-8").write(f"# TEMPLATE copied from hachiko: rewrite for {name}\n" + s)
    print("created", d)

if __name__ == "__main__":
    code, step = sys.argv[1], sys.argv[2]
    {"voice": voice, "preview": preview, "render": render, "qc": qc}.get(step, lambda c: new(c, sys.argv[3]) if step == "new" else None)(code)
