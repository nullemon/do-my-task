"""10s 9:16 Roblox-style skit: voiced characters, pseudo-3D turnarounds from front/side/back sheets."""
import math, os, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

BASE = "/tmp/claude-0/-home-user-do-my-task/2bcae0ac-8e61-53db-a931-9dcf67a790bf"
IMG, SP = f"{BASE}/images", f"{BASE}/scratchpad"
OUT, VO = f"{SP}/frames2", f"{SP}/vo"
W, H, FPS, DUR = 1080, 1920, 30, 10.0
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

# --- voice lines: (file, start time, speaker) ---
LINES = [("kakashi", 1.05, "kakashi"), ("sasuke1", 3.15, "sasuke"), ("sasuke2", 4.40, "sasuke"),
         ("kakashi2", 5.55, "kakashi"), ("naruto", 7.30, "naruto"), ("obito", 8.80, "obito")]
def readwav(p):
    with wave.open(p) as w: return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
VOX = {f: readwav(f"{VO}/{f}.wav") for f, _, _ in LINES}
def talk_env(who, t):
    """0..1 loudness of this character's voice at time t (drives talk bounce)."""
    for f, st, sp in LINES:
        if sp != who: continue
        i = int((t - st) * SR)
        x = VOX[f]
        if 0 <= i < len(x):
            seg = x[max(0, i - 700): i + 700]
            return min(1.0, float(np.sqrt((seg ** 2).mean())) * 5)
    return 0.0

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

SC = [(0.0, 2.2, "blue"), (2.2, 4.25, "purple"), (4.25, 6.8, "red"), (6.8, 8.35, "orange"), (8.35, 10.0, "end")]

def render(T):
    for a, b, key in SC:
        if a <= T < b: break
    t = T - a
    cv = BG[key].copy()
    shake = None
    if key == "blue":                                   # Kakashi strolls in, turns to camera
        building(cv, "blue", t)
        x, walking = walk_in(T, 0.05, 0.85, 1450, 740)
        v, sq = ("sideL", 1.0) if T < 0.85 else turn(["sideL", "front"], (T - 0.85) / 0.22)
        actor(cv, "kakashi", v, x, T, sq, walk=walking)
    elif key == "purple":                               # Sasuke walks in, turns, deadpan
        building(cv, "purple", t)
        x, walking = walk_in(T, 2.25, 2.9, -400, 330)
        v, sq = ("sideR", 1.0) if T < 2.9 else turn(["sideR", "front"], (T - 2.9) / 0.22)
        actor(cv, "sasuke", v, x, T, sq, walk=walking)
    elif key == "red":                                  # Sasuke yells; Kakashi (facing away) turns
        building(cv, "red", t)
        kv, ksq = ("back", 1.0) if T < 5.2 else turn(["back", "sideR", "front"], (T - 5.2) / 0.35)
        actor(cv, "kakashi", kv, 790, T, ksq)
        actor(cv, "sasuke", "front", 290, T, scale=1.0 + (0.08 if 4.4 < T < 5.25 else 0))
        if 4.4 < T < 5.25:
            shake = (int(np.random.randint(-16, 17)), int(np.random.randint(-16, 17)))
    elif key == "orange":                               # Naruto drops in spinning 360
        building(cv, "orange", t)
        drop = 1 - ease_back((T - 6.8) / 0.45)
        spin = (T - 6.8) / 0.5
        v, sq = turn(["front", "sideL", "back", "sideR", "front"], spin)
        hop = abs(math.sin((T - 7.3) * 9)) * 70 if T > 7.3 else 0
        actor(cv, "naruto", v, W / 2, T, sq, scale=1.06, lift=drop * 1400 + hop,
              rot=math.sin(T * 16) * 5 if T > 7.3 else 0)
    else:                                               # Reveal: all 4 HQs SOLD, masked guy turns around
        for j, k in enumerate(["blue", "purple", "red", "orange"]):
            gx, gy = 280 + (j % 2) * 520, 520 + (j // 2) * 330
            ap = 8.35 + 0.1 * j
            if T > ap:
                s = max(ease_back((T - ap) / 0.25), 0.05)
                paste(cv, HQS[k], gx, gy, s, s)
                if T > ap + 0.2:
                    st = Image.new("RGBA", (360, 130)); sd = ImageDraw.Draw(st)
                    from PIL import ImageFont
                    sd.rounded_rectangle((6, 6, 354, 124), 20, outline=(220, 20, 20, 255), width=12)
                    sd.text((180, 65), "SOLD", font=ImageFont.truetype(
                        "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf", 84), fill=(220, 20, 20), anchor="mm")
                    ss = 1.6 - 0.8 * ease((T - ap - 0.2) / 0.12)
                    paste(cv, st, gx, gy - 90, ss, ss, -14)
        v, sq = ("back", 1.0) if T < 8.5 else turn(["back", "sideL", "front"], (T - 8.5) / 0.3)
        actor(cv, "obito", v, W / 2, T, sq, scale=1.12)
    # slow camera push-in per scene (depth feel)
    z = 1 + 0.045 * (t / (b - a))
    if z > 1.001:
        cw, ch = int(W / z), int(H / z)
        cv = cv.crop(((W - cw) // 2, (H - ch) // 2 + 60, (W - cw) // 2 + cw, (H - ch) // 2 + 60 + ch)).resize((W, H), Image.BILINEAR)
    for a2, _, _ in SC[1:]:
        if 0 <= T - a2 < 0.1:
            cv.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(255 * (1 - (T - a2) / 0.1)))))
    if shake: cv = Image.fromarray(np.roll(np.array(cv), shake, axis=(0, 1)))
    return cv.convert("RGB")

np.random.seed(2)
N = int(DUR * FPS)
for f in range(int(os.environ.get("START", "0")), int(os.environ.get("END", N))):
    render(f / FPS).save(f"{OUT}/f{f:04d}.png")

# --- audio: voices + light SFX ---
aud = np.zeros(int(SR * DUR), np.float32)
def add(t0, sig, g=1.0):
    i = int(t0 * SR); n = min(len(sig), len(aud) - i); aud[i:i + n] += sig[:n] * g
def tone(f0, f1, d, vol=0.3, sq=False):
    n = int(SR * d); tt = np.arange(n) / SR
    ph = 2 * np.pi * np.cumsum(np.linspace(f0, f1, n)) / SR
    w = np.sign(np.sin(ph)) * 0.5 if sq else np.sin(ph)
    return (w * np.exp(-tt * 6 / d) * vol).astype(np.float32)
whoosh = lambda: (np.random.randn(int(SR * .22)) * np.linspace(0, 1, int(SR * .22)) ** 2 * .18).astype(np.float32)
for f, st, _ in LINES: add(st, VOX[f], 0.95)
for k in range(5): add(0.1 + k * 0.16, tone(180, 140, .06, .12))           # footsteps
for k in range(4): add(2.3 + k * 0.15, tone(180, 140, .06, .12))
for a2, _, _ in SC[1:]: add(a2 - 0.18, whoosh()); add(a2, tone(900, 250, .15, .25))
add(5.2, tone(400, 800, .25, .12))                                          # turn swish
add(6.8, tone(1400, 300, .45, .2)); add(7.25, tone(120, 60, .2, .5, True))  # fall + land
for j in range(4): add(8.55 + 0.1 * j, tone(140, 90, .09, .45, True))       # SOLD stamps
add(8.5, tone(300, 900, .25, .12))
peak = np.abs(aud).max(); aud = aud / max(peak, 1e-6) * 0.95
with wave.open(f"{SP}/audio2.wav", "wb") as wv:
    wv.setnchannels(1); wv.setsampwidth(2); wv.setframerate(SR)
    wv.writeframes((aud * 32000).astype(np.int16).tobytes())
print("done")
