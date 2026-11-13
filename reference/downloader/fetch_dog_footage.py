# -*- coding: utf-8 -*-
"""
Dog story footage fetcher.
Downloads (per story):  YouTube clips at 480p (+ subtitles), Pexels stock clips, web image search (DuckDuckGo/Bing), Openverse,
Wikimedia Commons + Library of Congress photos.  Then zips each story into parts < 390 MB.

Usage:  python fetch_dog_footage.py            -> asks which stories (Enter = 1-6)
        python fetch_dog_footage.py 1-6        -> stories 1..6
        python fetch_dog_footage.py 7,8,9,10   -> those stories
        python fetch_dog_footage.py all
        python fetch_dog_footage.py zip 1-6    -> only re-zip
        python fetch_dog_footage.py transcripts 1-6  -> Whisper transcripts for already-downloaded clips
                                                         (+ a tiny zip with only the transcripts)
"""
import os, sys

# --- MUST be first: this env var breaks Python HTTPS on this PC ("virtual_file.log") ---
for _k in list(os.environ):
    if _k.upper() == "SSLKEYLOGFILE":
        os.environ.pop(_k, None)

import re, csv, json, math, time, random, shutil, zipfile, traceback, datetime, subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE / "DogFootage"
ZIPS = OUT / "_ZIPS_TO_UPLOAD"
LOG = BASE / "fetch_log.txt"
KEYS = BASE / "keys.txt"
ZIP_LIMIT = 390 * 1024 * 1024
YT_MAX_FILESIZE = 150 * 1024 * 1024
STOCK_MAX_BYTES = 90 * 1024 * 1024
UA = "DogStoryFootageFetcher/1.0 (personal video research) python-requests"


# ----------------------------------------------------------------- logging (screen + file)
class Tee:
    def __init__(self, stream, path):
        self.stream = stream
        self.f = open(path, "a", encoding="utf-8", errors="replace")
    def write(self, s):
        try: self.stream.write(s)
        except Exception:
            try: self.stream.write(s.encode("ascii", "replace").decode())
            except Exception: pass
        self.f.write(s); self.f.flush()
    def flush(self):
        try: self.stream.flush()
        except Exception: pass
        self.f.flush()

sys.stdout = Tee(sys.stdout, LOG)
sys.stderr = Tee(sys.stderr, LOG)

def log(*a):
    print(datetime.datetime.now().strftime("%H:%M:%S"), *a, flush=True)

try:
    import requests
    from PIL import Image
    import yt_dlp
    from yt_dlp.utils import DownloadError
except Exception as e:
    log("ERROR: a Python package is missing:", e)
    log("Re-run the .bat file - it installs everything automatically.")
    sys.exit(1)

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG = shutil.which("ffmpeg")

# make the venv's Scripts folder (deno.exe lives there) and WinGet links visible to yt-dlp
os.environ["PATH"] = os.pathsep.join([
    str(Path(sys.executable).parent),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Links"),
    os.path.join(os.path.expanduser("~"), ".deno", "bin"),
    os.environ.get("PATH", "")])

SESSION = requests.Session()
SESSION.headers["User-Agent"] = UA


# ======================================================================== STORIES
# yt: list of (search query, [keywords - at least one must be in the video title] or None = story kw)
STORIES = {
 1: dict(slug="01_bobbie_wonder_dog", kw=["bobbie", "wonder dog", "silverton"], subs=["en"], max_dur=1500,
    yt=[("Bobbie the Wonder Dog Silverton Oregon", None),
        ("Call of the West 1924 Bobbie Oregon Historical Society", ["call of the west", "bobbie"]),
        ("Silverton Oregon Bobbie mural", None),
        ("Silverton Pet Parade Bobbie", None),
        ("Bobbie Wonder Dog grave Oregon Humane Society", None),
        ("Silverton Oregon downtown", ["silverton"])],
    stock=["collie dog walking", "dog walking alone road", "snowy mountains winter", "desert highway",
           "river crossing", "dog paws", "vintage car", "small town main street", "family hugging dog",
           "dog sleeping by fire"],
    commons=["Bobbie the Wonder Dog", "Silverton Oregon", "Silverton Oregon mural", "Wolcott Indiana",
             "Oregon Humane Society"],
    web=["Bobbie the Wonder Dog Silverton", "Bobbie the Wonder Dog 1924 photo", "Silverton Bobbie mural", "Bobbie Wonder Dog Brazier family", "Bobbie Wonder Dog doghouse Silverton", "Call of the West 1924 Bobbie"],
    loc=["Bobbie wonder dog Oregon"]),
 2: dict(slug="02_max_aurora", kw=["max", "aurora", "heeler", "warwick", "deaf"], subs=["en"], max_dur=900,
    yt=[("Max blue heeler Aurora lost Warwick", None),
        ("deaf blind dog stays with lost girl Queensland", None),
        ("Max honorary police dog Queensland", None),
        ("Aurora found dog Max grandmother Leisa Bennett", None),
        ("Warwick Queensland Aurora found search", ["aurora", "warwick"])],
    stock=["australian cattle dog", "blue heeler", "australian bush", "night forest rain", "old dog",
           "police search", "mountain sunrise", "dog sleeping grass", "eucalyptus hills", "grandmother hug"],
    commons=["Warwick Queensland", "Southern Downs Queensland", "Australian Cattle Dog blue"],
    web=["Max blue heeler Aurora Queensland", "Max deaf blind dog honorary police dog", "Aurora Max dog Warwick", "Leisa Bennett Aurora Max", "Queensland police Max good boy"],
    loc=[]),
 3: dict(slug="03_madison_camp_fire", kw=["madison", "gaylord", "guarded", "guarding"], subs=["en"], max_dur=900,
    yt=[("Madison dog guarded home Camp Fire Paradise", None),
        ("Andrea Gaylord Madison dog reunion", None),
        ("K9 Paw Print Rescue Shayla Sullivan Madison", None),
        ("Camp Fire Paradise November 8 2018 news footage", ["camp fire", "paradise"]),
        ("Paradise California after Camp Fire aerial", ["camp fire", "paradise"]),
        ("Camp Fire Paradise evacuation drive", ["camp fire", "paradise"])],
    stock=["wildfire", "forest fire night", "burned house ruins", "smoke forest", "anatolian shepherd",
           "great pyrenees", "dog waiting", "dog food bowl", "woman hugging dog", "ash rain"],
    commons=["Camp Fire 2018", "Paradise California Camp Fire", "Anatolian Shepherd"],
    web=["Madison Anatolian shepherd Camp Fire Paradise", "Madison dog guarded home Paradise", "Andrea Gaylord Madison dog", "Madison Miguel dogs Camp Fire reunion", "Camp Fire Paradise 2018 destruction"],
    loc=[]),
 4: dict(slug="04_frida_navy", kw=["frida", "perrita"], subs=["en", "es"], max_dur=900,
    yt=[("Frida rescue dog Mexico earthquake 2017", ["frida"]),
        ("Frida perrita rescatista Marina sismo", ["frida"]),
        ("Frida Semar retiro 2019", ["frida"]),
        ("Frida estatua Puebla perrita", ["frida"]),
        ("Frida rescue dog dies 2022", ["frida"]),
        ("Mexico earthquake September 19 2017 rescue footage", ["earthquake", "sismo", "quake"])],
    stock=["labrador retriever", "rubble", "earthquake damage building", "mexico city skyline",
           "rescue workers", "search and rescue dog", "candles vigil", "yellow labrador running", "dog boots"],
    commons=["Frida (dog)", "2017 Puebla earthquake", "Colegio Enrique Rébsamen", "Secretaría de Marina canine"],
    web=["Frida rescue dog Mexican Navy goggles", "Frida perrita rescatista", "Frida dog statue Puebla", "Frida rescue dog Israel Arauz", "Frida retirement ceremony Marina 2019"],
    loc=[]),
 5: dict(slug="05_bear_koala", kw=["bear", "koala detection", "detection dog"], subs=["en"], max_dur=900,
    yt=[("Bear koala detection dog IFAW", ["bear"]),
        ("Bear dog koalas bushfire", ["bear"]),
        ("University of the Sunshine Coast detection dogs Bear koala", None),
        ("Bear koala dog IFAW Animal Action Award", ["bear"]),
        ("Australian bushfires 2019 2020 koala rescue", ["koala"])],
    stock=["koala", "bushfire australia", "burnt forest", "eucalyptus forest", "border collie running",
           "dog playing ball", "smoke orange sky", "drone forest", "wildlife rescue", "kangaroo"],
    commons=["Koala", "2019–20 Australian bushfire season", "Australian Koolie", "koala burn"],
    web=["Bear koala detection dog", "Bear dog koala IFAW", "Bear koolie koala rescue", "koala burned bushfire rescue 2020"],
    loc=[]),
 6: dict(slug="06_togo_serum_run", kw=["togo", "balto", "serum", "seppala", "nome"], subs=["en"], max_dur=1800,
    yt=[("Togo sled dog 1925 serum run history", None),
        ("Leonhard Seppala footage", ["seppala"]),
        ("Balto 1925 newsreel real footage", ["balto", "1925"]),
        ("1925 serum run to Nome documentary", None),
        ("Balto statue Central Park", ["balto"]),
        ("Togo Balto Cleveland Museum of Natural History", ["balto", "togo"]),
        ("Iditarod Nome sled dogs news", ["iditarod", "nome"])],
    stock=["siberian husky", "sled dogs snow", "blizzard", "snow storm night", "frozen sea ice",
           "alaska winter", "northern lights", "husky running snow", "frozen tundra", "snowy cabin"],
    commons=["Togo Seppala sled dog", "Leonhard Seppala", "Balto (dog)", "1925 serum run to Nome", "Nome Alaska 1920s",
             "Gunnar Kaasen", "Balto statue Central Park"],
    web=["Togo sled dog Seppala", "Leonhard Seppala Togo 1925", "Balto Gunnar Kaasen 1925", "1925 serum run Nome map", "Togo Seppala team photo", "Balto statue Central Park"],
    loc=["Balto dog", "Seppala", "Nome Alaska sled dog"]),
 7: dict(slug="07_hachiko", kw=["hachiko", "hachikō", "ハチ", "akita"], subs=["en", "ja"], max_dur=1500,
    yt=[("Hachiko real footage 1934", None),
        ("忠犬ハチ公 実写 映像", None),
        ("忠犬ハチ公 生前 映像 1934", None),
        ("Hachiko real photos history", None),
        ("忠犬ハチ公 映像", None),
        ("忠犬ハチ公 NHK", None),
        ("Hachiko bark recording", None),
        ("Hachiko stuffed museum Ueno Tokyo", None),
        ("Hachiko Odate statue Akita", None),
        ("Hachiko 80th anniversary statue University of Tokyo 2015", None),
        ("Hachiko statue Shibuya", None),
        ("Hachiko Ueno statue University of Tokyo", None),
        ("Hachiko National Museum of Nature and Science", None),
        ("Shibuya station 1930s footage", ["shibuya", "渋谷", "1930"])],
    stock=["akita dog", "train station", "tokyo train", "shibuya", "cherry blossom", "snow falling",
           "dog waiting", "rain station platform", "old train"],
    commons=["Hachikō", "Hidesaburō Ueno", "Shibuya Station 1930s", "Hachiko statue", "Hachikō 1934"],
    web=["Hachiko real photo", "Hachiko 1934 statue ceremony", "Hachiko Hidesaburo Ueno", "Hachiko Shibuya station old photo", "Hachiko statue Shibuya"],
    loc=[]),
 8: dict(slug="08_capitan", kw=["capitán", "capitan", "carlos paz", "tumba", "grave", "cementerio"], subs=["en", "es"], max_dur=900,
    yt=[("Capitán perro cementerio Villa Carlos Paz", None),
        ("Capitan dog owner's grave Argentina", None),
        ("Capitán murió cementerio Carlos Paz", None),
        ("monumento perro Capitán Carlos Paz", None)],
    stock=["german shepherd", "cemetery", "dog lying grass", "sunset hills", "flowers grave", "rain",
           "dog walking street", "candle", "argentina mountains"],
    commons=["Villa Carlos Paz", "Capitán dog Carlos Paz", "Villa Carlos Paz cemetery"],
    web=["Capitan dog grave Villa Carlos Paz", "Capitán perro cementerio Carlos Paz", "Capitán Miguel Guzmán tumba perro", "monumento perro Capitán Carlos Paz"],
    loc=[]),
 9: dict(slug="09_sergeant_stubby", kw=["stubby", "102nd", "yankee division", "ww1", "wwi", "world war i"], subs=["en"], max_dur=1800,
    yt=[("Sergeant Stubby Smithsonian", ["stubby"]),
        ("Sergeant Stubby WWI dog history", ["stubby"]),
        ("Stubby statue Connecticut Veterans", ["stubby"]),
        ("102nd Infantry Yankee Division 1918 footage", None),
        ("WWI trenches real footage 1918", ["1918", "wwi", "ww1", "world war"]),
        ("WWI gas masks footage", ["gas"])],
    stock=["boston terrier", "bull terrier", "fog field", "barbed wire", "american flag", "medal",
           "parade", "old letters", "candle dark"],
    commons=["Sergeant Stubby", "Stubby dog 1919", "102nd Infantry Regiment 1918", "Yankee Division 1918",
             "World War I gas mask dog"],
    web=["Sergeant Stubby photo", "Sergeant Stubby Robert Conroy", "Sergeant Stubby medals coat Smithsonian", "Stubby dog gas mask WWI", "Sergeant Stubby Pershing medal"],
    loc=["Sergeant Stubby", "Stubby dog", "dog gas mask 1918", "26th Division 1918"]),
 10: dict(slug="10_patron_ukraine", kw=["patron", "патрон"], subs=["en", "uk"], max_dur=900,
    yt=[("Patron dog Ukraine mines", None),
        ("Patron dog Zelensky medal Trudeau", None),
        ("Пес Патрон ДСНС", None),
        ("Patron Jack Russell sapper dog", None),
        ("Patron dog Chernihiv", None)],
    stock=["jack russell terrier", "sunflower field", "wheat field", "children playing park",
           "dog running field", "dog cheese", "small dog vest", "hospital hallway"],
    commons=["Patron (dog)", "Patron dog Ukraine"],
    web=["Patron dog Ukraine", "Patron Jack Russell mine sniffing", "Patron dog Zelensky medal", "Patron dog Mykhailo Iliev", "пес Патрон"],
    loc=[]),
}

PREFERRED = ["abc news", "abc10", "abc7", "abc 7", "9 news", "9news", "7news", "10 news", "sbs", "cbs", "nbc",
    "good morning america", "today", "bbc", "reuters", "associated press", "ap archive", "afp", "guardian",
    "sky news", "cnn", "fox", "kcra", "krcr", "kxtv", "koin", "kgw", "katu", "kptv", "oregon historical",
    "ifaw", "sunshine coast", "smithsonian", "national park service", "alaska public", "ktuu", "anchorage",
    "iditarod", "milenio", "el universal", "televisa", "n+", "semar", "marina", "la voz", "telefe", "tn ",
    "clarín", "ukrinform", "дснс", "dsns", "nhk", "ann", "tbs", "fnn", "pbs", "wfsb", "global news", "cbc",
    "euronews", "dw ", "france 24", "al jazeera", "itv", "channel 4", "wion", "inside edition", "usa today",
    "washington post", "new york times", "national archives", "british pathé", "british pathe", "periscope film"]
BLOCK_TITLE = ["compilation", "reaction", "react ", "reacts", "top 10", "top 5", "top 7", "top10", "tiktok",
    "funny", "meme", "ai generated", "ai voice", "cartoon", "animated", "animation", "trailer", "full movie",
    "movie clip", "disney", "fan made", "fanmade", "asmr", "prank", "try not to cry", "storytime",
    "story time", "kids story", "bedtime", "minecraft", "roblox", "edit ", "amv", "lyrics"]
BLOCK_CHANNEL = ["kreeper", "minutes", "info", "stories", "facts", "tales", "compilation", "react", "viral", "top ", "kids", "cartoon",
    "trending", "mysteries", "explained", "anime"]


# ================================================================ helpers
def slugify(s, n=60):
    s = re.sub(r"[^\w\-]+", "_", s, flags=re.ASCII).strip("_")
    return (s[:n] or "item").lower()

class RateLimited(Exception):
    pass

def http_get(url, *, params=None, headers=None, stream=False, timeout=60, tries=7, max_wait=None):
    """GET with polite retry on 429/5xx (honours Retry-After).
    If the server asks for a wait longer than max_wait, raise RateLimited instead of sleeping."""
    for i in range(tries):
        try:
            r = SESSION.get(url, params=params, headers=headers, stream=stream, timeout=timeout)
        except requests.RequestException as e:
            wait = min(10 * 2 ** i, 240)
            log(f"   network error ({e.__class__.__name__}); retry in {wait}s")
            time.sleep(wait); continue
        if r.status_code in (429, 500, 502, 503, 504):
            ra = r.headers.get("Retry-After", "")
            wait = int(ra) if ra.isdigit() else min(20 * 2 ** i, 300)
            wait += random.randint(1, 5)
            if max_wait is not None and wait > max_wait:
                r.close()
                raise RateLimited(wait)
            log(f"   HTTP {r.status_code} (rate limit) - waiting {wait}s then retrying ({i+1}/{tries})")
            r.close(); time.sleep(wait); continue
        return r
    return None

def save_stream(r, dest, max_bytes=None):
    tmp = Path(str(dest) + ".part")
    n = 0
    with open(tmp, "wb") as f:
        for chunk in r.iter_content(1 << 16):
            n += len(chunk)
            if max_bytes and n > max_bytes:
                f.close(); tmp.unlink(missing_ok=True)
                return False
            f.write(chunk)
    tmp.replace(dest)
    return True

def download_image(url, dest, headers=None, attempts=4, http_tries=7, quiet=False, max_wait=None):
    """Download and VERIFY it is a real image (Commons sometimes returns HTML/error pages)."""
    for attempt in range(attempts):
        r = http_get(url, stream=True, headers=headers, tries=http_tries, timeout=30, max_wait=max_wait)
        if r is None or r.status_code != 200:
            if not quiet: log(f"   image failed (HTTP {getattr(r, 'status_code', '-')}) {url}")
            if attempts > 1: time.sleep(15 * (attempt + 1))
            continue
        ctype = r.headers.get("Content-Type", "")
        if not ctype.startswith("image/"):
            if not quiet: log(f"   not an image ({ctype})")
            r.close()
            if attempts > 1: time.sleep(20 * (attempt + 1))
            continue
        if not save_stream(r, dest, 60 * 1024 * 1024):
            return False
        try:
            if dest.stat().st_size < 8000:
                raise ValueError("too small")
            with Image.open(dest) as im: im.verify()
            with Image.open(dest) as im: w, h = im.size
            return (w, h)
        except Exception as e:
            if not quiet: log(f"   bad image file ({e})")
            dest.unlink(missing_ok=True)
            if attempts > 1: time.sleep(15 * (attempt + 1))
    return False

def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()

class Manifest:
    COLS = ["type", "moment", "file", "source_url", "title", "author_or_channel", "license_or_note",
            "duration_s", "width", "height", "views", "upload_date"]
    def __init__(self, folder):
        self.path = folder / "manifest.csv"
        self.rows = []
        self.seen = set()
        if self.path.exists():
            with open(self.path, encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    self.rows.append(row); self.seen.add(row["source_url"])
    # ---- "done" record so finished searches are skipped on re-runs
    def _done_path(self): return self.path.parent / "_done_searches.json"
    def is_done(self, key):
        if not hasattr(self, "_done"):
            try: self._done = set(json.loads(self._done_path().read_text(encoding="utf-8")))
            except Exception: self._done = set()
        return key in self._done
    def mark(self, key):
        self.is_done(key); self._done.add(key)
        self._done_path().write_text(json.dumps(sorted(self._done), ensure_ascii=False, indent=0), encoding="utf-8")
    def add(self, **kw):
        row = {c: kw.get(c, "") for c in self.COLS}
        self.rows.append(row); self.seen.add(row["source_url"]); self.save()
    def save(self):
        with open(self.path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=self.COLS); w.writeheader(); w.writerows(self.rows)


# ================================================================ keys
def load_keys():
    keys = {"PEXELS_KEY": os.environ.get("PEXELS_KEY", "")}
    if KEYS.exists():
        for line in KEYS.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                if k.strip() in keys and v.strip(): keys[k.strip()] = v.strip()
    else:
        print("\n  Free Pexels stock-video key (optional - press Enter to skip, add it later in keys.txt)")
        print("  Get one free at: https://www.pexels.com/api/")
        try:
            keys["PEXELS_KEY"] = input("  Paste Pexels API key: ").strip() or keys["PEXELS_KEY"]
        except EOFError:
            pass
        KEYS.write_text(f"PEXELS_KEY={keys['PEXELS_KEY']}\n", encoding="utf-8")
        log(f"Saved keys to {KEYS.name}")
    return keys


# ================================================================ YouTube
COOKIE_BROWSER = os.environ.get("YT_COOKIES_BROWSER") or None
SUB_FAILS = 0          # after 2 subtitle rate-limits, stop asking for subtitles this run
TRIED_COOKIES = False

def yt_search(query, n=12):
    opts = {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist", "skip_download": True}
    if COOKIE_BROWSER: opts["cookiesfrombrowser"] = (COOKIE_BROWSER,)
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch{n}:{query}", download=False)
    return [e for e in (info or {}).get("entries", []) if e and e.get("id")]

def score_entry(e, kws, max_dur):
    title = (e.get("title") or "").lower()
    chan = (e.get("channel") or e.get("uploader") or "").lower()
    dur = e.get("duration")
    if dur is not None and (dur < 12 or dur > max_dur): return None
    if any(b in title for b in BLOCK_TITLE): return None
    if any(b in chan for b in BLOCK_CHANNEL): return None
    if kws and not any(k.lower() in title for k in kws): return None
    s = 0.0
    raw_chan = e.get("channel") or e.get("uploader") or ""
    if any(p in chan for p in PREFERRED) or re.match(r"^[KW][A-Z]{2,3}(\b|-| |\d)", raw_chan): s += 50
    s += 3 * math.log10((e.get("view_count") or 0) + 1)
    if dur and dur > 600: s -= (dur - 600) / 150
    return s

def yt_download(url, outdir, subs):
    global COOKIE_BROWSER, TRIED_COOKIES, SUB_FAILS
    base = {
        "format": ("bv*[height<=480][ext=mp4]+ba[ext=m4a]/b[height<=480][ext=mp4]/"
                   "bv*[height<=480]+ba/b[height<=480]/wv*+ba/w"),
        "merge_output_format": "mp4",
        "outtmpl": str(outdir / "%(id)s.%(ext)s"),
        "noplaylist": True, "noprogress": True, "quiet": False, "no_warnings": False,
        "retries": 10, "fragment_retries": 10, "concurrent_fragment_downloads": 3,
        "max_filesize": YT_MAX_FILESIZE, "overwrites": False,
        "writesubtitles": True, "writeautomaticsub": True, "subtitlesformat": "vtt",
        "subtitleslangs": subs, "sleep_interval_subtitles": 2,
        "sleep_interval": 2, "max_sleep_interval": 6,
    }
    if FFMPEG: base["ffmpeg_location"] = FFMPEG
    nosubs = dict(writesubtitles=False, writeautomaticsub=False)
    attempts = [nosubs] if SUB_FAILS >= 2 else [dict(), nosubs]
    for extra in attempts:
        opts = dict(base, **extra)
        if COOKIE_BROWSER: opts["cookiesfrombrowser"] = (COOKIE_BROWSER,)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=True)
        except DownloadError as e:
            msg = str(e)
            if ("not a bot" in msg or "Sign in to confirm" in msg) and not TRIED_COOKIES:
                TRIED_COOKIES = True
                for b in ["firefox", "edge", "chrome", "brave"]:
                    log(f"   YouTube bot-check - trying cookies from {b} browser...")
                    try:
                        with yt_dlp.YoutubeDL(dict(opts, cookiesfrombrowser=(b,))) as ydl:
                            info = ydl.extract_info(url, download=True)
                        COOKIE_BROWSER = b; log(f"   cookies from {b} work - using them from now on")
                        return info
                    except Exception as e2:
                        log(f"   {b}: {str(e2)[:120]}")
                log("   Could not pass YouTube bot-check. Tip: sign in to YouTube in Firefox, close it, re-run.")
                return None
            if "subtitle" in msg.lower() and extra == {}:
                SUB_FAILS += 1
                log("   subtitle download failed - retrying without subtitles"
                    + ("  (subtitles now OFF for the rest of this run)" if SUB_FAILS >= 2 else ""))
                continue
            log(f"   download failed: {msg[:200]}")
            return None
        except Exception as e:
            log(f"   download error: {e}")
            return None
    return None

def do_youtube(sid, st, folder, man):
    ydir = folder / "youtube"; ydir.mkdir(parents=True, exist_ok=True)
    taken = {u.rsplit("/", 1)[-1] for u in man.seen if "youtu" in u}
    for mi, (q, kws) in enumerate(st["yt"], 1):
        kws = st["kw"] if kws is None else kws
        mdir = ydir / f"m{mi:02d}_{slugify(q, 40)}"
        have = sum(1 for r in man.rows if r["type"] == "youtube" and r["moment"].startswith(f"m{mi:02d} "))
        if have >= 2 or man.is_done(f"yt:{q}"):
            log(f"[{st['slug']}] YouTube moment {mi}: done before ({have} clips) - skipping"); continue
        log(f"[{st['slug']}] YouTube moment {mi}: {q}")
        try:
            entries = yt_search(q)
        except Exception as e:
            log(f"   search failed: {e}"); continue
        ranked = []
        for e in entries:
            if e["id"] in taken: continue
            s = score_entry(e, kws, st["max_dur"])
            if s is not None: ranked.append((s, e))
        ranked.sort(key=lambda t: -t[0])
        if not ranked:
            log("   no suitable match (all filtered out)"); man.mark(f"yt:{q}"); continue
        got = have
        for i_r, (s, e) in enumerate(ranked):
            if got >= 2: break
            if got >= 1 and s < 25:          # second clip only if it is a good source
                break
            url = f"https://youtu.be/{e['id']}"
            chan = e.get("channel") or e.get("uploader") or "?"
            log(f"   -> {e.get('title')}  [{chan}]  {e.get('duration')}s  score {s:.0f}")
            mdir.mkdir(parents=True, exist_ok=True)
            info = yt_download(url, mdir, st["subs"])
            files = [p for p in mdir.glob(f"{e['id']}.*") if p.suffix.lower() in (".mp4", ".webm", ".mkv")]
            if not info or not files:
                continue
            taken.add(e["id"]); got += 1
            man.add(type="youtube", moment=f"m{mi:02d} {q}", file=str(files[0].relative_to(folder)),
                    source_url=url, title=info.get("title", ""), author_or_channel=info.get("channel") or chan,
                    license_or_note="YouTube - credit channel on screen", duration_s=info.get("duration", ""),
                    width=info.get("width", ""), height=info.get("height", ""),
                    views=info.get("view_count", ""), upload_date=info.get("upload_date", ""))
        man.mark(f"yt:{q}")


# ================================================================ stock video
USED_STOCK = set()

def do_pexels(st, folder, man, key):
    sdir = folder / "stock"; sdir.mkdir(parents=True, exist_ok=True)
    for q in st["stock"]:
        if man.is_done(f"pexels:{q}"): continue
        r = http_get("https://api.pexels.com/videos/search", headers={"Authorization": key},
                     params={"query": q, "per_page": 15, "orientation": "landscape", "size": "medium"})
        if r is None or r.status_code != 200:
            log(f"   Pexels '{q}': HTTP {getattr(r, 'status_code', '-')}");
            if r is not None and r.status_code in (401, 403): log("   Pexels key rejected - check keys.txt"); return
            continue
        for v in r.json().get("videos", []):
            pid = f"pexels{v['id']}"
            if pid in USED_STOCK or v.get("url") in man.seen: continue
            files = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("width")]
            hd = [f for f in files if 1280 <= f["width"] <= 1920] or [f for f in files if f["width"] <= 1920]
            if not hd: continue
            f = max(hd, key=lambda x: x["width"])
            dest = sdir / f"pexels_{slugify(q, 30)}_{v['id']}.mp4"
            rr = http_get(f["link"], stream=True)
            if rr is None or rr.status_code != 200 or not save_stream(rr, dest, STOCK_MAX_BYTES): continue
            USED_STOCK.add(pid)
            man.add(type="stock_pexels", moment=q, file=str(dest.relative_to(folder)), source_url=v["url"],
                    title=q, author_or_channel=v.get("user", {}).get("name", ""), license_or_note="Pexels License",
                    duration_s=v.get("duration", ""), width=f["width"], height=f.get("height", ""))
            log(f"   Pexels '{q}' -> {dest.name}")
            break
        man.mark(f"pexels:{q}")
        time.sleep(1)


# ================================================================ photos
DEFERRED = []          # (story, folder, manifest, [queries]) to retry at the end of the run

def do_commons(st, folder, man, queries=None, max_wait=90):
    pdir = folder / "photos_commons"; pdir.mkdir(parents=True, exist_ok=True)
    queries = list(st["commons"] if queries is None else queries)
    for qi, q in enumerate(queries):
        if man.is_done(f"commons:{q}"):
            log(f"[{st['slug']}] Commons: {q} - done before, skipping"); continue
        try:
            _commons_query(st, folder, man, pdir, q, max_wait)
            man.mark(f"commons:{q}")
        except RateLimited as e:
            log(f"   Wikimedia asks to wait {e.args[0]}s - moving on, will come back to "
                f"{len(queries) - qi} Commons search(es) at the end")
            DEFERRED.append((st, folder, man, queries[qi:]))
            return

def _commons_query(st, folder, man, pdir, q, max_wait):
    api = "https://commons.wikimedia.org/w/api.php"
    if True:
        log(f"[{st['slug']}] Commons: {q}")
        named = any(k.lower() in q.lower() for k in st["kw"])
        per_query = 12 if named else 6           # place/general searches: only the top few
        r = http_get(api, max_wait=max_wait, params={"action": "query", "format": "json", "generator": "search",
                    "gsrsearch": f"{q} filetype:bitmap", "gsrnamespace": 6, "gsrlimit": per_query,
                    "prop": "imageinfo", "iiprop": "url|mime|size|extmetadata", "iiurlwidth": 1280,
                    "iiextmetadatafilter": "Artist|LicenseShortName|ImageDescription"})
        if r is None or r.status_code != 200:
            log(f"   search failed HTTP {getattr(r, 'status_code', '-')}"); return
        pages = (r.json().get("query") or {}).get("pages", {})
        for p in sorted(pages.values(), key=lambda p: p.get("index", 99)):
            ii = (p.get("imageinfo") or [{}])[0]
            page_url = ii.get("descriptionurl", "")
            if not ii or page_url in man.seen: continue
            if ii.get("mime") not in ("image/jpeg", "image/png"): continue
            if (ii.get("width") or 0) < 500: continue
            if named and not any(k.lower() in p["title"].lower() for k in st["kw"]): continue
            url = ii.get("thumburl") or ii.get("url")
            ext = ".png" if ii["mime"] == "image/png" else ".jpg"
            dest = pdir / (slugify(p["title"].replace("File:", ""), 70) + ext)
            time.sleep(3)                        # be polite - avoids 429
            ok = download_image(url, dest, max_wait=max_wait)
            if not ok: continue
            md = ii.get("extmetadata", {})
            man.add(type="photo_commons", moment=q, file=str(dest.relative_to(folder)), source_url=page_url,
                    title=p["title"], author_or_channel=strip_html(md.get("Artist", {}).get("value", ""))[:150],
                    license_or_note=md.get("LicenseShortName", {}).get("value", ""), width=ok[0], height=ok[1])
            log(f"   saved {dest.name} {ok[0]}x{ok[1]}")
        time.sleep(3)

# ---------------------------------------------------------------- web image search (DuckDuckGo + Bing)
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
SKIP_DOMAINS = ["gettyimages", "shutterstock", "alamy", "istockphoto", "dreamstime", "123rf", "depositphotos",
    "stock.adobe", "agefotostock", "pinterest", "pinimg", "lookaside", "fbsbx", "instagram", "tiktok",
    "redbubble", "etsy", "amazon", "ebay", "teepublic", "zazzle", "pond5", "vectorstock", "freepik",
    "craiyon", "lexica", "openart", "nightcafe"]

def _int(x):
    try: return int(float(x))
    except Exception: return 0

def ddg_images(q, n=40):
    try:
        from ddgs import DDGS
        res = DDGS().images(q, max_results=n, safesearch="moderate")
        return [dict(img=r.get("image"), page=r.get("url"), title=r.get("title", ""),
                     w=_int(r.get("width")), h=_int(r.get("height"))) for r in res if r.get("image")]
    except Exception as e:
        log(f"   DuckDuckGo images failed: {str(e)[:120]}")
        return []

def bing_images(q, n=35):
    import html as _html
    r = http_get("https://www.bing.com/images/async", tries=3,
                 params={"q": q, "first": 0, "count": n, "mmasync": 1, "adlt": "moderate"},
                 headers={"User-Agent": BROWSER_UA, "Accept-Language": "en-US,en;q=0.9"})
    if r is None or r.status_code != 200:
        log(f"   Bing images failed HTTP {getattr(r, 'status_code', '-')}"); return []
    out = []
    for m in re.finditer(r'\bm="(\{.*?\})"', r.text):
        try:
            d = json.loads(_html.unescape(m.group(1)))
            if d.get("murl"): out.append(dict(img=d["murl"], page=d.get("purl", ""), title=d.get("t", ""), w=0, h=0))
        except Exception:
            pass
    return out

def ahash(path):
    with Image.open(path) as im:
        im = im.convert("L").resize((8, 8))
        px = list(im.getdata())
    avg = sum(px) / 64
    return sum(1 << i for i, v in enumerate(px) if v > avg)

def do_web_images(st, folder, man, per_query=8, min_side=600):
    if not st.get("web"): return
    wdir = folder / "photos_web"; wdir.mkdir(parents=True, exist_ok=True)
    hashes = []
    for p in wdir.glob("*.jpg"):
        try: hashes.append(ahash(p))
        except Exception: pass
    seen_img = {row.get("title_img") for row in man.rows}
    for q in st["web"]:
        if man.is_done(f"web:{q}"):
            log(f"[{st['slug']}] Web images: {q} - done before, skipping"); continue
        log(f"[{st['slug']}] Web images: {q}")
        cands = ddg_images(q) + bing_images(q)
        got, tried = 0, set()
        for c in cands:
            if got >= per_query: break
            url, page = c["img"], c.get("page") or ""
            if url in tried or url in man.seen: continue
            tried.add(url)
            low = (url + " " + page).lower()
            if any(d in low for d in SKIP_DOMAINS): continue
            if _int(c.get("w")) and _int(c.get("h")) and min(_int(c["w"]), _int(c["h"])) < min_side: continue
            tmp = wdir / "_tmp_download.img"
            ok = download_image(url, tmp, headers={"User-Agent": BROWSER_UA, "Referer": page or url},
                                attempts=1, http_tries=2, quiet=True)
            if not ok: continue
            if min(ok) < min_side:
                tmp.unlink(missing_ok=True); continue
            try:
                h = ahash(tmp)
                if any(bin(h ^ x).count("1") <= 6 for x in hashes):      # same photo, other size/site
                    tmp.unlink(missing_ok=True); continue
                dest = wdir / f"{slugify(q, 35)}_{got+1:02d}_{slugify(c.get('title',''), 30)}.jpg"
                with Image.open(tmp) as im:
                    im.convert("RGB").save(dest, "JPEG", quality=93)
                tmp.unlink(missing_ok=True)
            except Exception as e:
                tmp.unlink(missing_ok=True); continue
            hashes.append(h); got += 1
            dom = re.sub(r"^https?://(www\.)?", "", page).split("/")[0]
            man.add(type="photo_web", moment=q, file=str(dest.relative_to(folder)), source_url=url,
                    title=c.get("title", "")[:150], author_or_channel=dom,
                    license_or_note=f"found via web search - page: {page}", width=ok[0], height=ok[1])
            log(f"   saved {dest.name} {ok[0]}x{ok[1]}  ({dom})")
        if got == 0: log("   nothing usable found")
        if cands: man.mark(f"web:{q}")             # only mark if the search itself worked
        time.sleep(2)

def do_openverse(st, folder, man, per_query=6, min_side=600):
    """Openverse = free search over Flickr / museums / other openly-licensed photos (no key)."""
    qs = list(dict.fromkeys((st.get("web") or [])[:4]))
    if not qs: return
    odir = folder / "photos_openverse"; odir.mkdir(parents=True, exist_ok=True)
    for q in qs:
        if man.is_done(f"openverse:{q}"): continue
        log(f"[{st['slug']}] Openverse: {q}")
        try:
            r = http_get("https://api.openverse.org/v1/images/", max_wait=120, tries=3,
                         params={"q": q, "page_size": 20, "mature": "false"})
        except RateLimited:
            log("   Openverse busy - skipping the rest for this story"); return
        if r is None or r.status_code != 200:
            log(f"   Openverse failed HTTP {getattr(r, 'status_code', '-')}"); continue
        got = 0
        for it in r.json().get("results", []):
            if got >= per_query: break
            page = it.get("foreign_landing_url") or it.get("url")
            if not it.get("url") or page in man.seen: continue
            w, h = _int(it.get("width")), _int(it.get("height"))
            if w and h and min(w, h) < min_side: continue
            title = it.get("title") or ""
            if any(k.lower() in q.lower() for k in st["kw"]) and not any(
                    k.lower() in (title + " " + " ".join(t.get("name", "") for t in it.get("tags") or [])).lower()
                    for k in st["kw"]):
                continue                                # dog-name search but photo isn't about this dog
            dest = odir / f"{slugify(q, 30)}_{slugify(title, 35)}_{str(it.get('id',''))[:8]}.jpg"
            try:
                ok = download_image(it["url"], dest, headers={"User-Agent": BROWSER_UA}, attempts=1,
                                    http_tries=2, quiet=True, max_wait=60)
            except RateLimited:
                ok = False
            if not ok or min(ok) < min_side:
                dest.unlink(missing_ok=True); continue
            got += 1
            lic = f"CC {it.get('license','').upper()} {it.get('license_version','')}".strip()
            man.add(type="photo_openverse", moment=q, file=str(dest.relative_to(folder)), source_url=page,
                    title=title[:150], author_or_channel=it.get("creator") or it.get("source", ""),
                    license_or_note=lic, width=ok[0], height=ok[1])
            log(f"   saved {dest.name} {ok[0]}x{ok[1]}  [{lic}]")
        man.mark(f"openverse:{q}")
        time.sleep(3)

def do_loc(st, folder, man, per_query=10):
    if not st.get("loc"): return
    pdir = folder / "photos_loc"; pdir.mkdir(parents=True, exist_ok=True)
    for q in st["loc"]:
        if man.is_done(f"loc:{q}"): continue
        log(f"[{st['slug']}] Library of Congress: {q}")
        r = http_get("https://www.loc.gov/photos/", params={"q": q, "fo": "json", "c": per_query},
                     headers={"User-Agent": BROWSER_UA, "Accept": "application/json"})
        if r is None or r.status_code != 200:
            log(f"   search failed HTTP {getattr(r, 'status_code', '-')}")
            if r is not None and r.status_code == 403:
                log("   Library of Congress is blocking automated searches - skipping it this run"); return
            continue
        try: results = r.json().get("results", [])
        except Exception: log("   LoC returned non-JSON"); continue
        man.mark(f"loc:{q}")
        for it in results:
            imgs = [u.split("#")[0] for u in it.get("image_url", []) if isinstance(u, str)]
            imgs = [("https:" + u) if u.startswith("//") else u for u in imgs]
            imgs = [u for u in imgs if u.lower().endswith((".jpg", ".jpeg", ".png"))]
            page = it.get("id") or it.get("url", "")
            if not imgs or page in man.seen: continue
            dest = pdir / (slugify(it.get("title", "loc"), 60) + "_" + slugify(page.rstrip("/").rsplit("/", 1)[-1], 20) + ".jpg")
            time.sleep(2)
            ok = download_image(imgs[-1], dest, headers={"User-Agent": BROWSER_UA}, attempts=2)
            if not ok: continue
            man.add(type="photo_loc", moment=q, file=str(dest.relative_to(folder)), source_url=page,
                    title=it.get("title", ""), author_or_channel="Library of Congress",
                    license_or_note="; ".join(it.get("rights", [])) if isinstance(it.get("rights"), list) else str(it.get("rights", "check LoC rights")),
                    width=ok[0], height=ok[1])
            log(f"   saved {dest.name} {ok[0]}x{ok[1]}")


# ================================================================ Whisper transcripts (runs on your NVIDIA GPU)
_WHISPER = None
def _add_cuda_dlls():
    try:
        import site
        for sp in site.getsitepackages() + [site.getusersitepackages()]:
            nv = Path(sp) / "nvidia"
            if nv.exists():
                for b in nv.glob("*/bin"):
                    try: os.add_dll_directory(str(b))
                    except Exception: pass
                    os.environ["PATH"] = str(b) + os.pathsep + os.environ["PATH"]
    except Exception:
        pass

def get_whisper():
    global _WHISPER
    if _WHISPER is not None: return _WHISPER
    try:
        _add_cuda_dlls()
        from faster_whisper import WhisperModel
    except Exception as e:
        log(f"   Whisper not available ({e}) - skipping transcripts"); _WHISPER = False; return False
    for dev, ct, name in [("cuda", "float16", "medium"), ("cpu", "int8", "small")]:
        try:
            log(f"   loading Whisper '{name}' on {dev.upper()} (first time downloads the model)...")
            _WHISPER = WhisperModel(name, device=dev, compute_type=ct)
            log(f"   Whisper ready on {dev.upper()}"); return _WHISPER
        except Exception as e:
            log(f"   Whisper on {dev} failed: {str(e)[:150]}")
    _WHISPER = False; return False

def do_transcripts(st, folder):
    vids = [p for p in (folder / "youtube").rglob("*.mp4")] if (folder / "youtube").exists() else []
    todo = [v for v in vids if not v.with_suffix(".transcript.json").exists()]
    if not todo: return
    m = get_whisper()
    if not m: return
    for v in todo:
        try:
            log(f"[{st['slug']}] transcribing {v.name}")
            segs, info = m.transcribe(str(v), word_timestamps=True, vad_filter=True)
            out = {"language": info.language, "segments": []}
            for sg in segs:
                out["segments"].append({"start": round(sg.start, 2), "end": round(sg.end, 2), "text": sg.text.strip(),
                    "words": [[w.word.strip(), round(w.start, 2), round(w.end, 2)] for w in (sg.words or [])]})
            if info.language != "en":
                tr, _ = m.transcribe(str(v), task="translate", vad_filter=True)
                out["english"] = [{"start": round(t.start, 2), "end": round(t.end, 2), "text": t.text.strip()} for t in tr]
            v.with_suffix(".transcript.json").write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
        except Exception as e:
            log(f"   transcript failed: {str(e)[:150]}")

def zip_transcripts(st):
    folder = OUT / st["slug"]; files = list(folder.rglob("*.transcript.json"))
    if not files: return None
    ZIPS.mkdir(parents=True, exist_ok=True); zp = ZIPS / f"{st['slug']}_TRANSCRIPTS.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files: z.write(p, arcname=str(Path(st["slug"]) / p.relative_to(folder)))
    log(f"   zip: {zp.name}  ({len(files)} transcripts, {zp.stat().st_size/1024:.0f} KB)")
    return zp

# ================================================================ zip
def zip_story(st):
    folder = OUT / st["slug"]
    if not folder.exists(): return []
    ZIPS.mkdir(parents=True, exist_ok=True)
    for old in ZIPS.glob(f"{st['slug']}_part*.zip"): old.unlink()
    files = [p for p in folder.rglob("*") if p.is_file() and not p.name.endswith((".part", ".ytdl", ".temp"))]
    first = [p for p in files if p.name == "manifest.csv"]
    rest = sorted([p for p in files if p.name != "manifest.csv"], key=lambda p: -p.stat().st_size)
    parts = [[0, []]]
    for p in first + rest:
        sz = p.stat().st_size
        for part in parts:
            if part[0] + sz <= ZIP_LIMIT: part[0] += sz; part[1].append(p); break
        else:
            parts.append([sz, [p]])
    out = []
    n = len(parts)
    for i, (_, plist) in enumerate(parts, 1):
        if not plist: continue
        zp = ZIPS / f"{st['slug']}_part{i}of{n}.zip"
        with zipfile.ZipFile(zp, "w") as z:
            for p in plist:
                comp = zipfile.ZIP_STORED if p.suffix.lower() in (".mp4", ".webm", ".mkv", ".jpg", ".png") else zipfile.ZIP_DEFLATED
                z.write(p, arcname=str(Path(st["slug"]) / p.relative_to(folder)), compress_type=comp)
        out.append(zp)
        log(f"   zip: {zp.name}  {zp.stat().st_size/1048576:.0f} MB")
    return out


# ================================================================ main
def parse_selection(s):
    s = (s or "").strip().lower()
    if not s: return [1, 2, 3, 4, 5, 6]
    if s == "all": return list(STORIES)
    sel = []
    for part in re.split(r"[,\s]+", s):
        if "-" in part:
            a, b = part.split("-", 1); sel += list(range(int(a), int(b) + 1))
        elif part.isdigit(): sel.append(int(part))
    return [i for i in dict.fromkeys(sel) if i in STORIES]

def main():
    log("=" * 70)
    log(f"Dog footage fetcher   python {sys.version.split()[0]}   yt-dlp {yt_dlp.version.__version__}")
    log(f"ffmpeg: {FFMPEG or 'NOT FOUND'}   deno: {shutil.which('deno') or 'not found (YouTube may be limited)'}")
    args = [a for a in sys.argv[1:] if a.strip()]
    zip_only = bool(args and args[0].lower() == "zip")
    tr_only = bool(args and args[0].lower() == "transcripts")
    if zip_only or tr_only: args = args[1:]
    if args:
        sel = parse_selection(" ".join(args))
    else:
        print("\n  Stories:")
        for i, st in STORIES.items(): print(f"   {i:2d}. {st['slug'][3:]}")
        try: ans = input("\n  Which stories? [Enter = 1-6, 'all' = 1-10, or e.g. 7-10]: ")
        except EOFError: ans = ""
        sel = parse_selection(ans)
    log("Selected stories:", sel)
    if tr_only:
        for sid in sel:
            st = STORIES[sid]; folder = OUT / st["slug"]
            if folder.exists(): do_transcripts(st, folder); zip_transcripts(st)
        log(f"Done. Upload the *_TRANSCRIPTS.zip files from: {ZIPS}")
        try: os.startfile(str(ZIPS))
        except Exception: pass
        return
    keys = {} if zip_only else load_keys()
    if not zip_only and not keys.get("PEXELS_KEY"):
        log("No Pexels key - skipping stock video (add it to keys.txt and re-run any time).")

    OUT.mkdir(exist_ok=True)
    summary = []
    for sid in sel:
        st = STORIES[sid]
        folder = OUT / st["slug"]; folder.mkdir(parents=True, exist_ok=True)
        man = Manifest(folder)
        log("-" * 70); log(f"STORY {sid}: {st['slug']}")
        if not zip_only:
            for name, fn in [("youtube", lambda: do_youtube(sid, st, folder, man)),
                             ("pexels", lambda: keys.get("PEXELS_KEY") and do_pexels(st, folder, man, keys["PEXELS_KEY"])),
                             ("web images", lambda: do_web_images(st, folder, man)),
                             ("openverse", lambda: do_openverse(st, folder, man)),
                             ("commons", lambda: do_commons(st, folder, man)),
                             ("loc", lambda: do_loc(st, folder, man)),
                             ("transcripts", lambda: do_transcripts(st, folder))]:
                try: fn()
                except KeyboardInterrupt: raise
                except Exception:
                    log(f"!! {name} step crashed (continuing):"); traceback.print_exc()
        summary.append((st, man))

    if DEFERRED and not zip_only:
        log("=" * 70); log("Catching up on Wikimedia searches that were rate-limited (waiting as asked)...")
        for st, folder, man, qs in list(DEFERRED):
            DEFERRED.remove((st, folder, man, qs))
            try: do_commons(st, folder, man, queries=qs, max_wait=None)
            except Exception: traceback.print_exc()

    done = []
    for st, man in summary:
        counts = {}
        for row in man.rows: counts[row["type"]] = counts.get(row["type"], 0) + 1
        done.append((st["slug"], counts, zip_story(st)))
    summary = done

    log("=" * 70); log("DONE. Summary:")
    for slug, counts, zips in summary:
        log(f"  {slug}: {counts}  ->  {len(zips)} zip(s)")
    log(f"Upload the zips from: {ZIPS}")
    log("Tip: upload them one story at a time (each part is under 400 MB).")
    try: os.startfile(str(ZIPS))
    except Exception: pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Stopped by user. Re-run any time - finished downloads are kept and skipped.")
    except Exception:
        log("FATAL ERROR:"); traceback.print_exc()
