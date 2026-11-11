"""10s 9:16 Roblox-style skit: voiced characters, pseudo-3D turnarounds from front/side/back sheets."""
import math, os, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

BASE = "/tmp/claude-0/-home-user-do-my-task/2bcae0ac-8e61-53db-a931-9dcf67a790bf"
IMG, SP = f"{BASE}/images", f"{BASE}/scratchpad"
OUT, VO = f"{SP}/frames4", f"{SP}/vo4"
W, H, FPS = 1080, 1920, 30
SR = 44100
os.makedirs(OUT, exist_ok=True)

def load(n): return Image.open(f"{IMG}/{n}.webp").convert("RGBA")
def crop_alpha(im): return im.crop(im.getchannel("A").point(lambda v: 255 if v > 10 else 0).getbbox())
def fit_h(im, h): return im.resize((int(im.width * h / im.height), h), Image.LANCZOS)
def fit_w(im, w): return im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)

# --- assets ---
HQ = {k: fit_w(crop_alpha(load(n)), 1000) for k, n in [("blue", 5), ("purple", 4), ("red", 7), ("orange", 6)]}
HQS = {k: fit_w(v, 440) for k, v in HQ.items()}
COLS = {8: [(18, 569), (596, 861), (883, 1435)], 9: [(41, 570), (588, 875), (876, 1408)],
        10: [(33, 542), (590, 891), (916, 1425)], 11: [(15, 530), (570, 893), (916, 1433)]}
CH = {}
for name, n in [("obito", 8), ("kakashi", 9), ("sasuke", 10), ("naruto", 11)]:
    im = load(n)
    views = [crop_alpha(im.crop((a - 3, 0, b + 3, im.height))) for a, b in COLS[n]]
    scale = 760 / views[0].height
    v = {k: vv.resize((int(vv.width * scale), int(vv.height * scale)), Image.LANCZOS)
         for k, vv in zip(["front", "sideL", "back"], views)}  # side views face left
    v["sideR"] = v["sideL"].transpose(Image.FLIP_LEFT_RIGHT)
    CH[name] = v

# --- background ---
def make_bg(tint):
    a = np.zeros((H, W, 3), np.float32)
    t = np.linspace(0, 1, H)[:, None]
    a[:] = (np.array([110, 185, 255]) * (1 - t) + np.array([205, 232, 255]) * t)[:, None, :]
    # perspective baseplate: grid lines converge toward horizon
    hz = 1350
    a[hz:] = [92, 170, 70]
    for k in range(1, 30):
        y = hz + int((k / 30) ** 1.8 * (H - hz))
        a[y:y + 3] = [78, 150, 60]
    yy, xx = np.mgrid[hz:H, 0:W]
    depth = (yy - hz) / (H - hz) + 0.05
    for gx in range(-20, 21):
        x_at = W / 2 + gx * 60 * depth * 3.2
        a[hz:][np.abs(xx - x_at) < 1.6] = [78, 150, 60]
    a[hz:hz + 10] = [70, 135, 52]
    a = a * 0.84 + np.array(tint) * 0.16
    return Image.fromarray(a.clip(0, 255).astype(np.uint8)).convert("RGBA")
BG = {"blue": make_bg((60, 90, 200)), "purple": make_bg((140, 60, 180)), "red": make_bg((210, 50, 50)),
      "orange": make_bg((255, 140, 30)), "end": make_bg((255, 205, 60))}

# --- helpers ---
def ease(t): t = min(max(t, 0), 1); return t * t * (3 - 2 * t)
def ease_back(t):
    t = min(max(t, 0), 1); c = 1.70158
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2

def paste(cv, im, cx, bottom, sx=1.0, sy=1.0, rot=0.0):
    if sx != 1 or sy != 1:
        im = im.resize((max(1, int(im.width * sx)), max(1, int(im.height * sy))), Image.LANCZOS)
    if rot: im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
    cv.alpha_composite(im, (int(cx - im.width / 2), int(bottom - im.height)))

def shadow(cv, cx, y, w, k=1.0):
    sh = Image.new("RGBA", (W, 200)); d = ImageDraw.Draw(sh)
    d.ellipse((cx - w / 2, 100 - 24, cx + w / 2, 100 + 24), fill=(0, 0, 0, int(95 * k)))
    cv.alpha_composite(sh.filter(ImageFilter.GaussianBlur(9)), (0, int(y - 100)))

def turn(seq, p):
    """Pseudo-3D turn through a sequence of views. Returns (view, x-squash)."""
    n = len(seq) - 1
    if p <= 0: return seq[0], 1.0
    if p >= 1: return seq[-1], 1.0
    seg = min(int(p * n), n - 1); q = p * n - seg
    sq = 0.45 + 0.55 * abs(math.cos(q * math.pi))       # narrow at the midpoint = turning
    return (seq[seg] if q < 0.5 else seq[seg + 1]), sq

def actor(cv, who, view, x, t, sx=1.0, scale=1.0, walk=False, lift=0.0, rot=0.0):
    im = CH[who][view]
    env = talk_env(who, t)
    talk = math.sin(t * 50) * 0.5 + 0.5
    sy = scale * (1 + 0.07 * env * talk)
    sxx = scale * sx * (1 - 0.035 * env * talk)
    bob = abs(math.sin(t * 12)) * 26 if walk else 0
    r = rot + (math.sin(t * 12) * 4 if walk else 0) + env * math.sin(t * 23) * 2.5
    shadow(cv, x, 1880, 310 * scale * max(sx, .5), k=max(0.35, 1 - lift / 400))
    paste(cv, im, x, 1882 - bob - lift, sxx, sy, r)

def building(cv, key, t):
    pop = 1 + 0.07 * max(0, 1 - t / 0.25)
    paste(cv, HQ[key], W / 2, 1385, pop, pop)

def walk_in(t, t0, t1, x0, x1):
    k = ease((t - t0) / (t1 - t0)); return x0 + (x1 - x0) * k, t0 <= t < t1


def readwav(p):
    with wave.open(p) as w: return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
VOX = {f: readwav(f"{VO}/{f}.wav") for f in ["kakashi", "sasuke1", "sasuke2", "kakashi2", "naruto", "obito"]}
D = {k: len(v) / SR for k, v in VOX.items()}

# ---- timeline built from voice lengths (local scene times) ----
S1 = dict(key="blue", line=0.85); S1["len"] = S1["line"] + D["kakashi"] + 0.5
S2 = dict(key="purple", line=0.75); S2["len"] = S2["line"] + D["sasuke1"] + 0.55
S3 = dict(key="red", line=0.25); S3["turn"] = S3["line"] + D["sasuke2"] + 0.2
S3["line2"] = S3["turn"] + 0.35; S3["len"] = S3["line2"] + D["kakashi2"] + 0.6
S4 = dict(key="orange", line=0.6); S4["len"] = S4["line"] + D["naruto"] + 0.55
S5 = dict(key="end", turn=0.55, line=1.0); S5["len"] = S5["line"] + D["obito"] + 0.9
SC, acc = [], 0.0
for sc in [S1, S2, S3, S4, S5]:
    sc["a"] = acc; acc += sc["len"]; SC.append(sc)
DUR = acc
LINES = [("kakashi", S1["a"] + S1["line"], "kakashi"), ("sasuke1", S2["a"] + S2["line"], "sasuke"),
         ("sasuke2", S3["a"] + S3["line"], "sasuke"), ("kakashi2", S3["a"] + S3["line2"], "kakashi"),
         ("naruto", S4["a"] + S4["line"], "naruto"), ("obito", S5["a"] + S5["line"], "obito")]

def talk_env(who, T):
    for f, st, sp in LINES:
        if sp != who: continue
        i = int((T - st) * SR); x = VOX[f]
        if 0 <= i < len(x):
            seg = x[max(0, i - 700): i + 700]
            return min(1.0, float(np.sqrt((seg ** 2).mean())) * 5)
    return 0.0

def wk(t, t0, t1, x0, x1):
    k = ease((t - t0) / (t1 - t0)); return x0 + (x1 - x0) * k, t0 <= t < t1

def render(T):
    sc = SC[-1]
    for c in SC:
        if c["a"] <= T < c["a"] + c["len"]: sc = c; break
    t = T - sc["a"]; key = sc["key"]
    cv = BG[key].copy(); shake = None
    if key == "blue":
        building(cv, "blue", t)
        x, w = wk(t, 0, 0.6, 1450, 740)
        v, sq = ("sideL", 1.0) if t < 0.6 else turn(["sideL", "front"], (t - 0.6) / 0.2)
        actor(cv, "kakashi", v, x, T, sq, walk=w)
    elif key == "purple":
        building(cv, "purple", t)
        x, w = wk(t, 0, 0.5, -400, 330)
        v, sq = ("sideR", 1.0) if t < 0.5 else turn(["sideR", "front"], (t - 0.5) / 0.18)
        actor(cv, "sasuke", v, x, T, sq, walk=w)
    elif key == "red":
        building(cv, "red", t)
        kv, ksq = ("back", 1.0) if t < sc["turn"] else turn(["back", "sideR", "front"], (t - sc["turn"]) / 0.3)
        actor(cv, "kakashi", kv, 790, T, ksq)
        yell = sc["line"] + 0.45 < t < sc["line"] + D["sasuke2"]   # "Who keeps doing this?"
        actor(cv, "sasuke", "front", 290, T, scale=1.0 + (0.08 if yell else 0))
        if yell: shake = (int(np.random.randint(-12, 13)), int(np.random.randint(-12, 13)))
    elif key == "orange":
        building(cv, "orange", t)
        drop = 1 - ease_back(t / 0.42)
        v, sq = turn(["front", "sideL", "back", "sideR", "front"], t / 0.5)
        hop = abs(math.sin((t - 0.45) * 8)) * 60 if t > 0.45 else 0
        actor(cv, "naruto", v, W / 2, T, sq, scale=1.06, lift=drop * 1400 + hop,
              rot=math.sin(T * 14) * 4 if t > 0.45 else 0)
    else:
        from PIL import ImageFont
        fnt = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf", 84)
        for j, k in enumerate(["blue", "purple", "red", "orange"]):
            gx, gy = 280 + (j % 2) * 520, 520 + (j // 2) * 330
            ap = 0.1 * j
            if t > ap:
                s_ = max(ease_back((t - ap) / 0.25), 0.05)
                paste(cv, HQS[k], gx, gy, s_, s_)
                stt = sc["line"] + 1.4 + 0.25 * j       # stamp as he says "to four different villages"
                if t > stt:
                    st = Image.new("RGBA", (360, 130)); sd = ImageDraw.Draw(st)
                    sd.rounded_rectangle((6, 6, 354, 124), 20, outline=(220, 20, 20, 255), width=12)
                    sd.text((180, 65), "SOLD", font=fnt, fill=(220, 20, 20), anchor="mm")
                    ss = 1.6 - 0.8 * ease((t - stt) / 0.12)
                    paste(cv, st, gx, gy - 90, ss, ss, -14)
        v, sq = ("back", 1.0) if t < sc["turn"] else turn(["back", "sideL", "front"], (t - sc["turn"]) / 0.35)
        actor(cv, "obito", v, W / 2, T, sq, scale=1.12)
    z = 1 + 0.045 * (t / sc["len"])
    cw, ch = int(W / z), int(H / z)
    cv = cv.crop(((W - cw) // 2, (H - ch) // 2 + 60, (W - cw) // 2 + cw, (H - ch) // 2 + 60 + ch)).resize((W, H), Image.BILINEAR)
    for c in SC[1:]:
        if 0 <= T - c["a"] < 0.1:
            cv.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(255 * (1 - (T - c["a"]) / 0.1)))))
    if shake: cv = Image.fromarray(np.roll(np.array(cv), shake, axis=(0, 1)))
    return cv.convert("RGB")

np.random.seed(2)
N = int(DUR * FPS)
if os.environ.get("INFO"): print(round(DUR, 2), N, [(c["key"], round(c["a"], 2)) for c in SC]); raise SystemExit
for f in range(int(os.environ.get("START", "0")), min(N, int(os.environ.get("END", N)))):
    render(f / FPS).save(f"{OUT}/f{f:04d}.png")

if os.environ.get("AUDIO"):
    aud = np.zeros(int(SR * DUR) + SR, np.float32)
    def add(t0, sig, g=1.0):
        i = int(t0 * SR); n = min(len(sig), len(aud) - i); aud[i:i + n] += sig[:n] * g
    def tone(f0, f1, d, vol=0.3, sq=False):
        n = int(SR * d); tt = np.arange(n) / SR
        ph = 2 * np.pi * np.cumsum(np.linspace(f0, f1, n)) / SR
        w = np.sign(np.sin(ph)) * 0.5 if sq else np.sin(ph)
        return (w * np.exp(-tt * 6 / d) * vol * 0.5).astype(np.float32)
    whoosh = lambda: (np.random.randn(int(SR * .22)) * np.linspace(0, 1, int(SR * .22)) ** 2 * .1).astype(np.float32)
    for f, st, _ in LINES: add(st, VOX[f], 1.0)
    for k in range(4): add(0.02 + k * 0.15, tone(180, 140, .06, .12))
    for k in range(3): add(S2["a"] + 0.02 + k * 0.15, tone(180, 140, .06, .12))
    for c in SC[1:]: add(c["a"] - 0.18, whoosh()); add(c["a"], tone(900, 250, .15, .2))
    add(S3["a"] + S3["turn"], tone(400, 800, .25, .1))
    add(S4["a"], tone(1400, 300, .4, .18)); add(S4["a"] + 0.4, tone(120, 60, .2, .45, True))
    for j in range(4): add(S5["a"] + S5["line"] + 1.4 + 0.25 * j, tone(140, 90, .09, .4, True))
    add(S5["a"] + S5["turn"], tone(300, 900, .3, .1))
    aud = aud[:int(SR * DUR)]
    aud = aud / max(np.abs(aud).max(), 1e-6) * 0.95
    with wave.open(f"{SP}/audio4.wav", "wb") as wv:
        wv.setnchannels(1); wv.setsampwidth(2); wv.setframerate(SR)
        wv.writeframes((aud * 32000).astype(np.int16).tobytes())
    print("audio done")
