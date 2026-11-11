import math, os, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

IMG = "/tmp/claude-0/-home-user-do-my-task/2bcae0ac-8e61-53db-a931-9dcf67a790bf/images"
OUT = "/tmp/claude-0/-home-user-do-my-task/2bcae0ac-8e61-53db-a931-9dcf67a790bf/scratchpad/frames"
W, H, FPS, DUR = 1080, 1920, 30, 10.0
os.makedirs(OUT, exist_ok=True)
FONT = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"

def load(n):
    return Image.open(f"{IMG}/{n}.webp").convert("RGBA")

def crop_alpha(im):
    return im.crop(im.getchannel("A").point(lambda v: 255 if v > 10 else 0).getbbox())

def fit(im, w=None, h=None):
    if w: return im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
    return im.resize((int(im.width * h / im.height), h), Image.LANCZOS)

hq = {k: crop_alpha(load(n)) for k, n in [("blue", 5), ("purple", 4), ("red", 7), ("orange", 6)]}
front = {"obito": (18, 569), "kakashi": (41, 570), "sasuke": (33, 542), "naruto": (15, 530)}
chars = {}
for name, n in [("obito", 8), ("kakashi", 9), ("sasuke", 10), ("naruto", 11)]:
    x0, x1 = front[name]
    chars[name] = fit(crop_alpha(load(n).crop((x0 - 5, 0, x1 + 5, 1086))), h=760)

# background: sky gradient + roblox-ish green baseplate with studs grid
def make_bg(tint):
    bg = Image.new("RGB", (W, H))
    a = np.zeros((H, W, 3), np.float32)
    top, bot = np.array([110, 185, 255]), np.array([200, 230, 255])
    t = np.linspace(0, 1, H)[:, None]
    a[:] = (top * (1 - t) + bot * t)[:, None, :]
    a[1350:] = [92, 170, 70]
    a[1350:1362] = [70, 140, 55]
    for y in range(1362, H, 60): a[y:y + 3] = [80, 155, 62]
    for x in range(0, W, 60): a[1362:, x:x + 3] = [80, 155, 62]
    a = a * 0.82 + np.array(tint) * 0.18
    return Image.fromarray(a.clip(0, 255).astype(np.uint8)).convert("RGBA")

bgs = {"blue": make_bg((60, 90, 200)), "purple": make_bg((140, 60, 180)),
       "red": make_bg((210, 50, 50)), "orange": make_bg((255, 140, 30)), "end": make_bg((255, 210, 60))}

def font(s): return ImageFont.truetype(FONT, s)

def text_c(d, cx, y, s, size, fill=(255, 255, 255), stroke=(0, 0, 0), sw=10):
    f = font(size)
    w = d.textlength(s, font=f)
    d.text((cx - w / 2, y), s, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke)

def bubble(canvas, x, y, lines, size=58, tail="down", tx=None):
    d = ImageDraw.Draw(canvas)
    f = font(size)
    tw = max(d.textlength(l, font=f) for l in lines)
    pad = 34
    bw, bh = tw + pad * 2, len(lines) * (size + 14) + pad * 2 - 14
    x = max(30, min(W - 30 - bw, x - bw / 2))
    d.rounded_rectangle((x, y, x + bw, y + bh), 40, fill="white", outline="black", width=8)
    tx = tx if tx is not None else x + bw / 2
    tx = max(x + 60, min(x + bw - 60, tx))
    if tail == "down":
        d.polygon([(tx - 30, y + bh - 6), (tx + 30, y + bh - 6), (tx - 10, y + bh + 60)], fill="white", outline="black")
        d.line([(tx - 30, y + bh - 2), (tx - 10, y + bh + 60), (tx + 30, y + bh - 2)], fill="black", width=8)
        d.line([(tx - 24, y + bh - 4), (tx + 24, y + bh - 4)], fill="white", width=8)
    for i, l in enumerate(lines):
        d.text((x + pad, y + pad + i * (size + 14)), l, font=f, fill="black")

def ease_out_back(t):
    t = min(max(t, 0), 1); c = 1.70158
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2

def paste(canvas, im, cx, bottom, scale=1.0, rot=0, alpha=1.0):
    if scale != 1.0: im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    if rot: im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
    if alpha < 1: im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(bottom - im.height)))

def shadow(canvas, cx, y, w):
    sh = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(sh)
    d.ellipse((cx - w / 2, y - 22, cx + w / 2, y + 22), fill=(0, 0, 0, 90))
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))

def building(canvas, key, t, punch=True):
    s = 1.0 + (0.08 * max(0, 1 - t / 0.25) if punch else 0)
    b = fit(hq[key], w=1000)
    paste(canvas, b, W / 2, 1380, scale=s)

def day_tag(canvas, label, t):
    d = ImageDraw.Draw(canvas)
    s = ease_out_back(t / 0.3)
    size = int(110 * max(s, 0.01))
    if size > 4: text_c(d, W / 2, 150 + (110 - size) / 2, label, size, fill=(255, 230, 60), sw=12)

def char(canvas, name, cx, t, enter=0.0, from_x=None, bob=True, scale=1.0, flip=False):
    im = chars[name].transpose(Image.FLIP_LEFT_RIGHT) if flip else chars[name]
    k = ease_out_back((t - enter) / 0.35)
    x = cx if from_x is None else from_x + (cx - from_x) * k
    by = 1880 - (abs(math.sin((t) * 9)) * 18 if bob else 0)
    shadow(canvas, x, 1878, 300 * scale)
    paste(canvas, im, x, by, scale=scale)

# ---- scenes: (start, end) ----
SC = [(0.0, 2.2), (2.2, 4.4), (4.4, 6.6), (6.6, 8.3), (8.3, 10.0)]

def render(tt):
    for i, (a, b) in enumerate(SC):
        if a <= tt < b: idx, t = i, tt - a; break
    else: idx, t = 4, tt - SC[4][0]
    keys = ["blue", "purple", "red", "orange", "end"]
    c = bgs[keys[idx]].copy()
    shake = (0, 0)
    if idx == 0:
        building(c, "blue", t)
        day_tag(c, "DAY 1", t)
        char(c, "kakashi", 760, t, enter=0.2, from_x=1500)
        if t > 0.7: bubble(c, 640, 580, ["New HQ just", "dropped. Nice."], tx=760)
    elif idx == 1:
        building(c, "purple", t)
        day_tag(c, "DAY 2", t)
        char(c, "sasuke", 330, t, enter=0.15, from_x=-500, bob=False)
        if t > 0.6: bubble(c, 380, 640, ["...it was BLUE", "yesterday."], tx=330)
    elif idx == 2:
        building(c, "red", t)
        day_tag(c, "DAY 3", t)
        char(c, "kakashi", 800, t, bob=False)
        char(c, "sasuke", 300, t, bob=False)
        if t > 0.35:
            bubble(c, 300, 560, ["WHO KEEPS", "DOING THIS?!"], size=66, tx=300)
            shake = (int(np.random.randint(-14, 15)), int(np.random.randint(-14, 15)))
        if t > 1.3: bubble(c, 820, 930, ["(didn't notice)"], size=44, tx=800)
    elif idx == 3:
        building(c, "orange", t)
        day_tag(c, "DAY 4", t)
        jump = abs(math.sin(t * 7)) * 120
        sc = 1.0 + 0.15 * ease_out_back(t / 0.3) - 0.15
        im = chars["naruto"]
        shadow(c, W / 2, 1878, 320)
        paste(c, im, W / 2, 1880 - jump, scale=1.05 * max(sc, 0.3), rot=math.sin(t * 14) * 6)
        if t > 0.25: bubble(c, W / 2, 520, ["ORANGE IS", "OBVIOUSLY BETTER!!"], size=62)
    else:
        # punchline: grid of 4 HQs with SOLD stamps, Obito in front
        d = ImageDraw.Draw(c)
        text_c(d, W / 2, 120, "MEANWHILE...", 90, fill=(255, 255, 255), sw=12)
        for j, k in enumerate(["blue", "purple", "red", "orange"]):
            gx, gy = 280 + (j % 2) * 520, 590 + (j // 2) * 330
            appear = 0.12 * j
            if t > appear:
                s = ease_out_back((t - appear) / 0.25)
                paste(c, fit(hq[k], w=440), gx, gy, scale=max(s, 0.05))
                if t > appear + 0.25:
                    st = Image.new("RGBA", (360, 130), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
                    sd.rounded_rectangle((6, 6, 354, 124), 20, outline=(220, 20, 20, 255), width=12)
                    sd.text((180, 65), "SOLD", font=font(84), fill=(220, 20, 20), anchor="mm")
                    paste(c, st, gx, gy - 90, scale=0.8, rot=-14)
        char(c, "obito", W / 2, t, enter=0.55, from_x=W / 2, bob=False,
             scale=0.95)
        if t > 0.9: bubble(c, W / 2, 960, ["Sold the same tower", "to 4 villages. :)"], size=56)
    # white flash at cuts
    for a, _ in SC[1:]:
        if 0 <= tt - a < 0.12:
            fl = Image.new("RGBA", (W, H), (255, 255, 255, int(255 * (1 - (tt - a) / 0.12))))
            c.alpha_composite(fl)
    if shake != (0, 0):
        c = Image.fromarray(np.roll(np.array(c), shake, axis=(0, 1)))
    return c.convert("RGB")

np.random.seed(1)
N = int(DUR * FPS)
for f in range(int(os.environ.get('START','0')), N):
    render(f / FPS).save(f"{OUT}/f{f:04d}.png")

# ---- audio: pops on cuts, boings for naruto, ding for punchline ----
SR = 44100
aud = np.zeros(int(SR * DUR), np.float32)
def add(t0, sig):
    i = int(t0 * SR); aud[i:i + len(sig)] += sig[:len(aud) - i]
def tone(f0, f1, d, vol=0.4, kind="sin"):
    n = int(SR * d); t = np.arange(n) / SR
    f = np.linspace(f0, f1, n); ph = 2 * np.pi * np.cumsum(f) / SR
    w = np.sin(ph) if kind == "sin" else np.sign(np.sin(ph)) * 0.5
    return (w * np.exp(-t * 6 / d) * vol).astype(np.float32)
whoosh = lambda: (np.random.randn(int(SR * .25)) * np.linspace(0, 1, int(SR * .25)) ** 2 * .25).astype(np.float32)
add(0.2, tone(300, 900, .15)); add(0.7, tone(700, 700, .08, .25))
for a, _ in SC[1:]: add(a - 0.2, whoosh()); add(a, tone(900, 200, .2, .45))
add(2.8, tone(700, 700, .08, .25))
for k in range(8): add(4.8 + k * 0.08, tone(120, 90, .07, .5, "sq"))  # angry rumble
for k in range(4): add(6.7 + k * 0.45, tone(200, 600, .25, .45))       # boing jumps
for j in range(4): add(8.3 + 0.12 * j + 0.25, tone(1200, 1200, .12, .3))  # stamps
add(9.2, tone(1568, 1568, .5, .35)); add(9.2, tone(2093, 2093, .6, .25))  # cha-ching
aud = np.clip(aud, -1, 1)
with wave.open(OUT + "/../audio.wav", "wb") as wv:
    wv.setnchannels(1); wv.setsampwidth(2); wv.setframerate(SR)
    wv.writeframes((aud * 32000).astype(np.int16).tobytes())
print("frames done")
