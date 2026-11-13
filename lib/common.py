"""Shared helpers: paths, fonts, case loading, encoder selection."""
import os, sys, subprocess, importlib, csv, functools, shutil
os.environ.pop("SSLKEYLOGFILE", None)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "lib")
FONTS = os.path.join(ROOT, "fonts")
MODELS = os.path.join(ROOT, "models")
FPS = 30

def case_dir(code):
    d = os.path.join(ROOT, "cases", code)
    if not os.path.isdir(d): raise SystemExit(f"no case folder: {d}")
    return d

def load_case(code):
    d = case_dir(code)
    if d not in sys.path: sys.path.insert(0, d)
    cfg = importlib.import_module("cfg"); scr = importlib.import_module("script")
    cfg.DIR = d; cfg.WORK = os.path.join(d, "work"); os.makedirs(cfg.WORK, exist_ok=True)
    cfg.PH = load_photos(d)
    return cfg, scr

def load_photos(d):
    """photos/manifest.csv -> {key: dict(file, credit)}; plus any extra rows in photos/extra.csv"""
    out = {}
    for name in ("manifest.csv", "extra.csv"):
        p = os.path.join(d, "photos", name)
        if not os.path.exists(p): continue
        for r in csv.DictReader(open(p, encoding="utf-8")):
            f = r["file"] if os.path.isabs(r["file"]) else os.path.join(d, r["file"])
            lic = r.get("lic", "")
            artist = r.get("artist", "").replace("Unknown authorUnknown author", "Unknown author")
            src = r.get("source", "Wikimedia Commons")
            credit = r.get("credit") or (f"{src} · {artist} · {lic}" if artist and "nknown" not in artist else f"{src} · {lic}")
            out[r["key"]] = dict(file=f, credit=credit, lic=lic, page=r.get("page", ""), title=r.get("title", ""))
    return out

@functools.lru_cache(maxsize=None)
def _font(name, size):
    from PIL import ImageFont
    return ImageFont.truetype(os.path.join(FONTS, name), max(6, int(size)))
def font(name, size): return _font(name, int(size))
MB, MXB, MSB, MM = "Montserrat_900Black.ttf", "Montserrat_800ExtraBold.ttf", "Montserrat_600SemiBold.ttf", "Montserrat_500Medium.ttf"
PF, PFB = "PlayfairDisplay_900Black.ttf", "PlayfairDisplay_700Bold.ttf"

def ffmpeg_bin():
    if shutil.which("ffmpeg"): return "ffmpeg"
    try:
        import imageio_ffmpeg; return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception: return "ffmpeg"
FF = ffmpeg_bin()
FP = shutil.which("ffprobe") or FF.replace("ffmpeg", "ffprobe")

@functools.lru_cache(maxsize=1)
def video_encoder():
    """h264_nvenc on an NVIDIA GPU when it really works, else libx264. Override with ENC=x264|nvenc."""
    want = os.environ.get("ENC", "")
    if want != "x264":
        try:
            r = subprocess.run([FF, "-v", "error", "-f", "lavfi", "-i", "color=black:s=256x256:d=0.2", "-c:v", "h264_nvenc", "-f", "null", "-"],
                               capture_output=True, timeout=30)
            if r.returncode == 0:
                return ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "20", "-b:v", "0", "-pix_fmt", "yuv420p"]
        except Exception: pass
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-threads", "2"]

def probe_dur(f):
    r = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)

def probe_wh(f):
    r = subprocess.run([FP, "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height", "-of", "csv=p=0", f],
                       capture_output=True, text=True).stdout.strip().split(",")
    return int(r[0]), int(r[1])
