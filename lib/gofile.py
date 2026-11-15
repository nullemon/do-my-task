"""python lib/gofile.py <code>  -> uploads deliver/*.mp4, thumbnails and the SEO txt into one Gofile folder; prints the link
(writes deliver/gofile_link.txt)."""
import os, sys, glob, requests
os.environ.pop("SSLKEYLOGFILE", None)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import case_dir
d = os.path.join(case_dir(sys.argv[1]), "deliver")
files = [f for f in sorted(glob.glob(os.path.join(d, "*"))) if os.path.isfile(f) and not os.path.basename(f).startswith("PREVIEW")
         and f.endswith((".mp4", ".jpg", ".txt")) and not f.endswith("gofile_link.txt")]
token = folder = link = None
for f in files:
    data = {"token": token, "folderId": folder} if token else {}
    for a in range(5):
        try:
            with open(f, "rb") as fh:
                j = requests.post("https://upload.gofile.io/uploadfile", data=data, files={"file": (os.path.basename(f), fh)}, timeout=3600).json()
            if j.get("status") == "ok": break
        except Exception as e: j = {"error": str(e)}
        print("retry", os.path.basename(f), str(j)[:150])
    dd = j["data"]; token = token or dd.get("guestToken"); folder = folder or dd.get("parentFolder"); link = link or dd.get("downloadPage")
    print("uploaded", os.path.basename(f), flush=True)
open(os.path.join(d, "gofile_link.txt"), "w").write(link + "\n"); print("LINK", link)
