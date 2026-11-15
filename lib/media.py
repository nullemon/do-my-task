"""python lib/media.py <code>   -> downloads cases/<code>/media.json items
  commons images -> photos/<key>.jpg  + photos/manifest.csv   (key, file, title, lic, artist, date, page, size, real)
  commons video (webm/ogv) and archive.org films -> footage/<key>.mp4 + footage/manifest.csv (key, file, credit, lic, page, dur)
Skips files that already exist. Polite to Wikimedia (spaced requests, long back-off on 429)."""
import os, sys, json, csv, re, time, subprocess
os.environ.pop("SSLKEYLOGFILE", None)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import case_dir, FF, probe_dur
import requests
from PIL import Image
S = requests.Session(); S.headers["User-Agent"] = "DogStoriesPipeline/1.0 (documentary research; contact via repository)"
API = "https://commons.wikimedia.org/w/api.php"

def get(url, **kw):
    for a in range(8):
        try:
            r = S.get(url, timeout=120, **kw)
            if r.status_code == 200: return r
            wait = int(r.headers.get("retry-after", "0") or 0) or 15 * (a + 1)
            print(f"   {r.status_code} -> wait {min(wait, 120)}s", flush=True); time.sleep(min(wait, 120))
        except Exception as e:
            print("   err", e); time.sleep(10)
    return None

def clean(s): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()

def commons_info(titles):
    out = {}
    for i in range(0, len(titles), 40):
        r = get(API, params=dict(action="query", titles="|".join("File:" + t for t in titles[i:i + 40]), prop="imageinfo",
                                 iiprop="url|size|mime|extmetadata", iiurlwidth=2000, format="json"))
        if not r: continue
        q = r.json().get("query", {}); norm = {n["to"]: n["from"] for n in q.get("normalized", [])}
        for p in q.get("pages", {}).values():
            if "imageinfo" not in p: continue
            ii = p["imageinfo"][0]; em = ii.get("extmetadata", {}); g = lambda k: clean(em.get(k, {}).get("value", ""))
            artist = g("Artist")
            for junk in ("Unknown authorUnknown author", "Unknown author"): artist = artist.replace(junk, "Unknown")
            t = p["title"][5:]
            out[norm.get(p["title"], p["title"])[5:]] = out[t] = dict(url=ii["url"], thumb=ii.get("thumburl"), mime=ii.get("mime", ""), w=ii.get("width"),
                h=ii.get("height"), lic=g("LicenseShortName") or "see page", artist=artist[:60], date=g("DateTimeOriginal")[:30],
                page="https://commons.wikimedia.org/wiki/File:" + t.replace(" ", "_"))
        time.sleep(2)
    return out

def to_mp4(src, dst, t_max=None):
    cmd = [FF, "-loglevel", "error", "-y", "-i", src] + (["-t", str(t_max)] if t_max else []) + [
        "-vf", "scale='min(1280,iw)':-2", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", dst]
    return subprocess.run(cmd).returncode == 0

def archive_best(ident):
    r = get(f"https://archive.org/metadata/{ident}")
    if not r: return None
    j = r.json(); files = j.get("files", [])
    cand = [f for f in files if f.get("name", "").lower().endswith((".mp4", ".ogv", ".mpeg4"))]
    cand.sort(key=lambda f: (0 if "512kb" in f["name"] or f.get("format") == "h.264" else 1, int(f.get("size", 0) or 0)))
    md = j.get("metadata", {})
    lic = md.get("licenseurl") or ("Public domain" if "public" in json.dumps(md).lower() else "see page")
    return (cand[0]["name"], md.get("title", ident), lic) if cand else None

def main(code):
    d = case_dir(code); items = json.load(open(os.path.join(d, "media.json"), encoding="utf-8"))
    os.makedirs(os.path.join(d, "photos"), exist_ok=True); os.makedirs(os.path.join(d, "footage"), exist_ok=True)
    pm = os.path.join(d, "photos", "manifest.csv"); fm = os.path.join(d, "footage", "manifest.csv")
    prow = {r["key"]: r for r in csv.DictReader(open(pm, encoding="utf-8"))} if os.path.exists(pm) else {}
    frow = {r["key"]: r for r in csv.DictReader(open(fm, encoding="utf-8"))} if os.path.exists(fm) else {}
    com = [x for x in items if x.get("type", "commons") == "commons" and x["key"] not in prow and x["key"] not in frow]
    info = commons_info([x["title"].replace("File:", "").replace("_", " ") for x in com]) if com else {}
    for x in items:
        k = x["key"]; typ = x.get("type", "commons")
        if k in prow or k in frow: continue
        if typ == "commons":
            t = x["title"].replace("File:", "").replace("_", " "); ii = info.get(t)
            if not ii: print("MISSING on Commons:", k, t); continue
            if ii["mime"].startswith("video") or t.lower().endswith((".webm", ".ogv")):
                raw = os.path.join(d, "footage", k + ".src"); r = get(ii["url"])
                if not r: continue
                open(raw, "wb").write(r.content); dst = os.path.join(d, "footage", k + ".mp4")
                if to_mp4(raw, dst, 600):
                    os.remove(raw)
                    frow[k] = dict(key=k, file=f"footage/{k}.mp4", credit=f"Wikimedia Commons · {ii['artist'] or 'Unknown'} · {ii['lic']}",
                                   lic=ii["lic"], page=ii["page"], dur=f"{probe_dur(dst):.1f}", shows=x.get("shows", ""))
                    print("video", k, frow[k]["dur"], "s")
                continue
            if ii["mime"] in ("application/pdf", "image/vnd.djvu"): print("skip doc", k); continue
            url = ii["thumb"] if (ii.get("w") or 0) > 2000 and ii.get("thumb") else ii["url"]
            r = get(url)
            if not r: print("FAILED", k); continue
            raw = os.path.join(d, "photos", k + ".raw"); open(raw, "wb").write(r.content)
            try:
                im = Image.open(raw); im.load(); im = im.convert("RGB")
                if max(im.size) > 2400: im.thumbnail((2400, 2400), Image.LANCZOS)
                im.save(os.path.join(d, "photos", k + ".jpg"), quality=93); os.remove(raw)
            except Exception as e:
                print("BAD image", k, e); os.remove(raw); continue
            prow[k] = dict(key=k, file=f"photos/{k}.jpg", title=t, lic=ii["lic"], artist=ii["artist"], date=ii["date"], page=ii["page"],
                           size=f"{im.width}x{im.height}", real=str(x.get("is_the_real_dog", "")), shows=x.get("shows", "")[:120])
            print("photo", k, im.size, ii["lic"], ii["artist"][:30], flush=True); time.sleep(3)
        elif typ == "archive":
            best = archive_best(x["title"])
            if not best: print("no video in archive item", x["title"]); continue
            name, title, lic = best; raw = os.path.join(d, "footage", k + ".src")
            print("archive", k, name, flush=True)
            with S.get(f"https://archive.org/download/{x['title']}/{name}", stream=True, timeout=600) as r:
                if r.status_code != 200: print("  failed", r.status_code); continue
                with open(raw, "wb") as fh:
                    for c in r.iter_content(1 << 20): fh.write(c)
            dst = os.path.join(d, "footage", k + ".mp4")
            if to_mp4(raw, dst):
                os.remove(raw)
                frow[k] = dict(key=k, file=f"footage/{k}.mp4", credit=x.get("author") or f"Internet Archive · {title[:50]}",
                               lic=x.get("license") or lic, page=f"https://archive.org/details/{x['title']}", dur=f"{probe_dur(dst):.1f}", shows=x.get("shows", ""))
                print("  ok", frow[k]["dur"], "s")
        else:
            print("manual source (not auto-downloaded):", k, typ, x.get("title"))
    for path, rows, fields in ((pm, prow, ["key", "file", "title", "lic", "artist", "date", "page", "size", "real", "shows"]),
                               (fm, frow, ["key", "file", "credit", "lic", "page", "dur", "shows"])):
        if rows:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows.values())
    print(f"{code}: {len(prow)} photos, {len(frow)} clips")

if __name__ == "__main__":
    for c in sys.argv[1:]: main(c)
