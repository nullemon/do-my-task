"""python lib/vidsearch.py <code> "query 1" "query 2" ...
Searches public-domain / CC video: Internet Archive (movies), Wikimedia Commons (video files), DVIDS (US military video).
Prints candidates and appends them to cases/<code>/video_candidates.json  (review, then add the ones you want to media.json)."""
import os, sys, json, re, subprocess, time, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import case_dir
UA = "DogStoriesPipeline/1.0 (documentary research)"

def curl(url):
    for a in range(6):
        p = subprocess.run(["curl", "-sS", "-L", "-m", "60", "-A", UA if "wikimedia" in url else "Mozilla/5.0", "-w", "\n%{http_code}", url], capture_output=True)
        body, _, code = p.stdout.rpartition(b"\n")
        if code == b"200": return body.decode("utf-8", "replace")
        if code in (b"429", b"503"): time.sleep(20 * (a + 1)); continue
        return None
    return None

def archive(q):
    u = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(
        {"q": f"({q}) AND mediatype:movies", "fl[]": ["identifier", "title", "year", "licenseurl", "runtime"], "rows": 15, "output": "json"}, doseq=True)
    h = curl(u)
    if not h: return []
    return [dict(type="archive", title=d["identifier"], name=d.get("title", ""), year=d.get("year", ""), license=d.get("licenseurl", ""),
                 runtime=d.get("runtime", "")) for d in json.loads(h)["response"]["docs"]]

def commons(q):
    u = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "list": "search", "srsearch": f"{q} filetype:video", "srnamespace": 6, "srlimit": 15, "format": "json"})
    h = curl(u); time.sleep(2)
    if not h: return []
    return [dict(type="commons", title=r["title"][5:], name=re.sub("<[^>]+>", "", r.get("snippet", ""))[:100]) for r in json.loads(h)["query"]["search"]]

def dvids(q):
    h = curl("https://www.dvidshub.net/search/?" + urllib.parse.urlencode({"q": q, "filter[type]": "video", "sort": "relevance"}))
    if not h: return []
    out = []
    for m in re.finditer(r'href="(/video/(\d+)/[^"]+)"[^>]*>([^<]{4,200})<', h):
        out.append(dict(type="dvids", title="https://www.dvidshub.net" + m.group(1), name=m.group(3).strip()))
    seen = set(); res = []
    for x in out:
        if x["title"] not in seen: seen.add(x["title"]); res.append(x)
    return res[:15]

if __name__ == "__main__":
    code = sys.argv[1]; d = case_dir(code); path = os.path.join(d, "video_candidates.json")
    allc = json.load(open(path)) if os.path.exists(path) else []
    have = {c["title"] for c in allc}
    for q in sys.argv[2:]:
        for fn in ((archive, dvids) if os.environ.get("NOCOMMONS") else (archive, commons, dvids)):
            try: res = fn(q)
            except Exception as e: print("  err", fn.__name__, e); res = []
            for r in res:
                r["query"] = q
                if r["title"] not in have:
                    have.add(r["title"]); allc.append(r)
                    print(f"[{r['type']:7s}] {r['title'][:70]:70s} | {r.get('name','')[:60]} {r.get('year','')} {r.get('license','')}")
    json.dump(allc, open(path, "w"), indent=1, ensure_ascii=False)
    print(len(allc), "candidates in", path)
