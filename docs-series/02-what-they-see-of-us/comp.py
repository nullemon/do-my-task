"""WHAT THEY SEE OF US - compositor. Builds every frame of the film from:
  * the Blender starfield loop (bgloop/bg_XXXX.png), time-remapped to the camera's log-distance
    and blended across neighbouring loop frames (motion blur when we move fast),
  * Blender stills of Earth and the Moon, numpy plates (sky, nebula), galaxy textures,
  * labels, leader lines, vignettes, counter and cards (Inter Light, PIL).
The camera model is identical to blender/bg_loop.py and timeline.py.

Usage: python3 comp.py --start A --end B --out seg.mp4      (pipes raw frames to ffmpeg)
       python3 comp.py --stills 120,1500 --outdir DIR         (PNG stills for checking)
"""
import os, sys, json, math, subprocess, argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
Image.MAX_IMAGE_PIXELS = None

HERE = os.path.dirname(os.path.abspath(__file__))
W_ = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/02-what-they-see-of-us"
TEX = os.path.join(W_, "tex")
BG = os.path.join(W_, "bgloop")
FONT_L = "/usr/share/fonts/opentype/inter/Inter-Light.otf"
FONT_XL = "/usr/share/fonts/opentype/inter/Inter-ExtraLight.otf"
FONT_R = "/usr/share/fonts/opentype/inter/Inter-Regular.otf"
TL = json.load(open(os.path.join(HERE, "timeline.json")))
FPS, NF, FOC = TL["fps"], TL["nframes"], TL["foc"]
KM, LS, AU = TL["km"], TL["ls"], TL["au"]
S = np.array(TL["s"])
WID, HEI = 1920, 1080
CX, CY = WID / 2, HEI / 2
LOOP_N, LOOP_DS = 192, 0.5
LINES = {l["key"]: l for l in TL["lines"]}

TXT = np.array([0.91, 0.925, 0.95], np.float32)
DIM = np.array([0.60, 0.64, 0.72], np.float32)
GOLD = np.array([0.96, 0.80, 0.52], np.float32)


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def win(t, t0, t1, fi=0.6, fo=0.6):
    return float(sstep(t0, t0 + fi, t) * (1 - sstep(t1 - fo, t1, t)))


# ------------------------------------------------------------------------------------ text
_fonts = {}
def font(path, size):
    k = (path, size)
    if k not in _fonts: _fonts[k] = ImageFont.truetype(path, size)
    return _fonts[k]


def text_img(lines, align="left"):
    """lines: list of (text, fontpath, size, colour(0..1), tracking px, gap_after). -> RGBA float array"""
    items, wmax, htot = [], 0, 0
    for (t, fp, sz, col, tr, gap) in lines:
        f = font(fp, sz)
        w = sum(f.getlength(ch) + tr for ch in t) - tr if t else 0
        asc, desc = f.getmetrics()
        items.append((t, f, col, tr, w, asc + desc, gap)); wmax = max(wmax, w); htot += asc + desc + gap
    im = Image.new("RGBA", (int(wmax) + 8, int(htot) + 8), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    y = 2
    for (t, f, col, tr, w, h, gap) in items:
        x = 2 if align == "left" else (wmax - w + 2 if align == "right" else (wmax - w) / 2 + 2)
        c = tuple(int(255 * v) for v in col)
        for ch in t:
            d.text((x, y), ch, font=f, fill=c + (255,)); x += f.getlength(ch) + tr
        y += h + gap
    # soft dark backing so thin text stays legible over bright galaxies
    a = im.split()[3].filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(6))
    pad = Image.new("RGBA", im.size, (0, 0, 0, 0))
    pad.putalpha(a.point(lambda v: int(v * 0.7)))
    pad.alpha_composite(im)
    return np.asarray(pad).astype(np.float32) / 255


def paste(frame, img, x, y, alpha=1.0):
    """alpha-composite an RGBA float image with its top-left at (x,y)."""
    if alpha <= 0.003: return
    h, w = img.shape[:2]; x, y = int(round(x)), int(round(y))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(WID, x + w), min(HEI, y + h)
    if x1 <= x0 or y1 <= y0: return
    sub = img[y0 - y:y1 - y, x0 - x:x1 - x]
    a = sub[..., 3:4] * alpha
    frame[y0:y1, x0:x1] = frame[y0:y1, x0:x1] * (1 - a) + sub[..., :3] * a


def add(frame, img, x, y, gain=1.0):
    h, w = img.shape[:2]; x, y = int(round(x)), int(round(y))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(WID, x + w), min(HEI, y + h)
    if x1 <= x0 or y1 <= y0: return
    frame[y0:y1, x0:x1] += img[y0 - y:y1 - y, x0 - x:x1 - x, :3] * gain


def glow(frame, x, y, col, amp, core=1.1, halo=7.0, halo_amp=0.12, spikes=0.0):
    """additive star glow at sub-pixel position."""
    if amp <= 0.002: return
    R = int(max(4 * core, 3.2 * halo)) + 2
    ix, iy = int(math.floor(x)), int(math.floor(y))
    if ix < -R or iy < -R or ix > WID + R or iy > HEI + R: return
    gy, gx = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
    dx, dy = gx - (x - ix), gy - (y - iy)
    r2 = dx * dx + dy * dy
    k = np.exp(-r2 / (2 * core * core)) + halo_amp * np.exp(-np.sqrt(r2) / halo)
    k *= np.clip(1 - r2 / (R * R), 0, 1) ** 2
    if spikes > 0:
        k += spikes * (np.exp(-np.abs(dy) / 0.7) * np.exp(-np.abs(dx) / (halo * 2.2)) +
                       np.exp(-np.abs(dx) / 0.7) * np.exp(-np.abs(dy) / (halo * 2.2)))
    img = (k * amp)[..., None] * np.asarray(col, np.float32)
    x0, y0 = ix - R, iy - R
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(WID, x0 + 2 * R + 1), min(HEI, y0 + 2 * R + 1)
    if xb <= xa or yb <= ya: return
    frame[ya:yb, xa:xb] += img[ya - y0:yb - y0, xa - x0:xb - x0]


_BIG = None
def big_glow(frame, x, y, amp):
    global _BIG
    if _BIG is None:
        R = 640
        gy, gx = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
        r2 = gx * gx + gy * gy
        k = (np.exp(-r2 / (2 * 60.0 ** 2)) + 0.3 * np.exp(-np.sqrt(r2) / 200.0)) * np.clip(1 - r2 / (R * R), 0, 1) ** 2
        _BIG = k[..., None] * np.array([1.0, 0.85, 0.65], np.float32)
    add(frame, _BIG * amp, x - 640, y - 640)


# ----------------------------------------------------------------------------------- assets
def load_rgb(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float32) / 255


SKY_IN = load_rgb(os.path.join(TEX, "sky_in.png"))
SKY_OUT = load_rgb(os.path.join(TEX, "sky_out.png"))
EARTH = Image.open(os.path.join(TEX, "earth_rgba.png")).convert("RGBA")
EARTH_R, EARTH_C = 558.0, 667.0
MOON = Image.open(os.path.join(TEX, "moon_rgba.png")).convert("RGBA")
_ma = np.asarray(MOON)[..., 3]; _xs = np.nonzero(_ma.max(0) > 128)[0]
MOON_R = (_xs.max() - _xs.min()) / 2; MOON_C = MOON.size[0] / 2
ORION = Image.open(os.path.join(TEX, "orion.png")).convert("RGB")
MW = Image.open(os.path.join(TEX, "mw.png")).convert("RGB")
MW_PYR = [MW] + [MW.resize((2048 >> k, 2048 >> k), Image.LANCZOS) for k in range(1, 7)]
M31T = Image.open(os.path.join(TEX, "m31.png")).convert("RGB")
LMCT = Image.open(os.path.join(TEX, "lmc.png")).convert("RGB")
VIG = {}
def vig(name):
    if name not in VIG:
        im = Image.open(os.path.join(TEX, f"vig_{name}.png")).convert("RGB").resize((416, 240), Image.LANCZOS)
        a = np.asarray(im).astype(np.float32) / 255
        VIG[name] = np.dstack([a, np.ones(a.shape[:2], np.float32)])
    return VIG[name]

_bg = {}
def bgframe(i):
    i %= LOOP_N
    if i not in _bg:
        if len(_bg) > 40:
            _bg.pop(next(iter(_bg)))
        _bg[i] = np.asarray(Image.open(os.path.join(BG, f"bg_{i:04d}.png")).convert("RGB"))
    return _bg[i]


def bg_stream(s0, s1):
    """loop phase for log-distance s, blended across [s0,s1] (motion blur)."""
    p0, p1 = s0 / LOOP_DS * LOOP_N, s1 / LOOP_DS * LOOP_N
    n = int(min(10, max(1, math.ceil(abs(p1 - p0)))))
    if n == 1:
        f = math.floor(p0); w = p0 - f
        return (bgframe(f) * ((1 - w) / 255.0)).astype(np.float32) + bgframe(f + 1) * np.float32(w / 255.0)
    acc = np.zeros((HEI, WID, 3), np.float32)
    for k in range(n):
        p = p0 + (p1 - p0) * (k + 0.5) / n if n > 1 else p0
        f = math.floor(p); w = p - f
        acc += bgframe(f).astype(np.float32) * (1 - w) + bgframe(f + 1).astype(np.float32) * w
    return acc / (255.0 * n)


# ---------------------------------------------------------------------------------- geometry
def obj_pos(o):
    th, ph = math.radians(o["th"]), math.radians(o["ph"])
    d = o["d"]
    return np.array([d * math.sin(th) * math.cos(ph), d * math.sin(th) * math.sin(ph), d * math.cos(th)])


def project(p, D):
    dz = D - p[2]
    if dz <= 0: return None
    return CX + FOC * p[0] / dz, CY - FOC * p[1] / dz, math.sqrt(p[0] ** 2 + p[1] ** 2 + dz ** 2), dz


OBJ = TL["obj"]
for o in OBJ: o["pos"] = obj_pos(o)
COLD = dict(TL["cold"]); COLD["pos"] = obj_pos(COLD)
OBJD = {o["key"]: o for o in OBJ}

# galaxy plane: centre = galactic-centre object, tilted so the flight climbs out at 40 deg
GCP = OBJD["gc"]["pos"]; g = GCP / np.linalg.norm(GCP)
zh = np.array([0, 0, 1.0]); h1 = zh - g * (zh @ g); h1 /= np.linalg.norm(h1); h2 = np.cross(g, h1)
cpsi = math.sin(math.radians(40)) / (h1 @ zh); psi = math.acos(min(1, cpsi))
NRM = math.cos(psi) * h1 + math.sin(psi) * h2
E1 = -g                                     # texture x axis: from the centre toward the Sun
rot = math.radians(118)                     # spin the texture so the Sun sits in an arm
E1, E2 = math.cos(rot) * E1 + math.sin(rot) * np.cross(NRM, E1), -math.sin(rot) * E1 + math.cos(rot) * np.cross(NRM, E1)
MW_HALF = 59000.0


def galaxy_layer(D):
    """perspective-warp the Milky Way texture onto the plane through the galactic centre."""
    cam = np.array([0, 0, D])
    scale_px = FOC * MW_HALF / D                     # rough on-screen half-size of the disc
    lvl = int(np.clip(math.floor(math.log2(max(1e-6, 1024 / max(scale_px, 1)))), 0, 6))
    tex = MW_PYR[lvl]; ts = tex.size[0]
    pts_s, pts_t = [], []
    for sx, sy in ((0, 0), (WID, 0), (WID, HEI), (0, HEI)):
        r = np.array([(sx - CX) / FOC, -(sy - CY) / FOC, -1.0])
        t = ((GCP - cam) @ NRM) / (r @ NRM)
        p = cam + t * r - GCP
        u = (p @ E1) / MW_HALF * ts / 2 + ts / 2; v = (p @ E2) / MW_HALF * ts / 2 + ts / 2
        pts_s.append((sx, sy)); pts_t.append((u, v))
    A, b = [], []
    for (x, y), (u, v) in zip(pts_s, pts_t):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    coef = np.linalg.solve(np.array(A), np.array(b))
    out = tex.transform((WID, HEI), Image.PERSPECTIVE, tuple(coef), Image.BILINEAR, fillcolor=(0, 0, 0))
    return np.asarray(out).astype(np.float32) / 255


def sprite_img(img, size, rotate=0.0, squash=1.0):
    w = max(2, int(size)); h = max(2, int(size * squash))
    im = img.resize((w, h), Image.LANCZOS if w < img.size[0] else Image.BICUBIC)
    if rotate:
        im = im.rotate(rotate, Image.BICUBIC, expand=True)
    return np.asarray(im).astype(np.float32) / 255


# ---------------------------------------------------------------------------------- labels
LBL = {}
def label_block(o, align):
    k = (o["key"], align)
    if k in LBL: return LBL[k]
    sees = o["sees"]
    head = "SEES EARTH AS IT WAS" if "AGO" in sees else "SEES EARTH IN"
    if o.get("minor"):
        lines = [(o["name"], FONT_L, 19, TXT * 0.85, 3, 2), (f"{o['dist']}  ·  {sees}", FONT_L, 16, DIM, 2, 0)]
    else:
        lines = [(o["name"], FONT_L, 31, TXT, 6, 6), (o["dist"], FONT_L, 19, DIM, 3, 14),
                 (head, FONT_L, 15, DIM, 4, 3), (sees, FONT_L, 40, GOLD, 3, 4)]
        if o.get("note"): lines.append((o["note"], FONT_L, 14, np.array([0.95, 0.6, 0.5]), 4, 0))
    LBL[k] = text_img(lines, align)
    return LBL[k]


CAP = {}
def caption(text, size=17, col=DIM, tr=4, font_=FONT_L, align="center"):
    k = (text, size, tuple(col), tr, align)
    if k not in CAP: CAP[k] = text_img([(text, font_, size, col, tr, 0)], align)
    return CAP[k]


def draw_label(frame, ov, o, x, y, a, inset=True, t=0):
    """leader line + text block on the outer side of the object; vignette inset bottom corner."""
    side = -1 if x < CX else 1
    lead = 46 if not o.get("minor") else 26
    bx, by = x + side * lead, y - lead * 0.8
    blk = label_block(o, "left" if side > 0 else "right")
    h, w = blk.shape[:2]
    tx = bx + side * 12 if side > 0 else bx - 12 - w
    if tx < 60 or tx + w > WID - 60:                      # flip inward if it would leave the frame
        side = -side; bx, by = x + side * lead, y - lead * 0.8
        blk = label_block(o, "left" if side > 0 else "right"); h, w = blk.shape[:2]
        tx = bx + side * 12 if side > 0 else bx - 12 - w
    ty = by - 18
    ty = min(max(ty, 50), HEI - h - 40)
    tx = min(max(tx, 30), WID - w - 30)
    al = int(255 * a * (0.55 if o.get("minor") else 0.8))
    r0 = 9 if not o.get("minor") else 5
    vx, vy = (bx - x), (by - y); n = math.hypot(vx, vy)
    ov.line([(x + vx / n * r0, y + vy / n * r0), (bx, by), (bx + side * 10, by)], fill=(225, 230, 240, al), width=1)
    paste(frame, blk, tx, ty, a)
    if inset and o.get("vig"):
        ia = a * win(t, o["show"][0] + 0.5, o["show"][1], 0.7, 0.6)
        draw_inset(frame, ov, o["vig"], o["cap"], "right" if x < CX else "left", ia)


def draw_inset(frame, ov, name, cap, corner, ia):
    if ia <= 0.003: return
    im = vig(name)
    ix = WID - 416 - 70 if corner == "right" else 70
    iy = HEI - 240 - 92
    paste(frame, im, ix, iy, ia * 0.94)
    c = caption(cap, 14, TXT * 0.9, 3)
    paste(frame, c, min(max(ix + 208 - c.shape[1] / 2, 24), WID - 24 - c.shape[1]), iy + 250, ia)
    e = caption("EARTH, AS SEEN FROM THERE", 12, DIM, 4)
    paste(frame, e, ix + 208 - e.shape[1] / 2, iy - 24, ia * 0.85)


# --------------------------------------------------------------------------------- counter
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
def fmt_lookback(D):
    sec = D / LS
    if sec < 60: return f"{sec:.1f} SECONDS AGO" if sec < 10 else f"{sec:.0f} SECONDS AGO"
    if sec < 3600: return f"{int(sec // 60)} MIN {int(sec % 60):02d} S AGO"
    if sec < 86400 * 2: return f"{sec / 3600:.1f} HOURS AGO"
    if D < 0.25: return f"{sec / 86400:.0f} DAYS AGO"
    y = TL["now"] - D
    if D < 40:
        m = int((y % 1) * 12); return f"{MONTHS[m]} {int(math.floor(y))}"
    if y >= 1000: return f"{int(round(y))}"
    if y >= 1: return f"AD {int(round(y))}"
    if D < 12000: return f"{int(round(-y + 1)):,} BC"
    if D < 1e6: return f"{int(round(D, -2 if D < 1e5 else -3)):,} YEARS AGO"
    return f"{D / 1e6:.1f} MILLION YEARS AGO" if D < 1e7 else f"{D / 1e6:.0f} MILLION YEARS AGO"


def fmt_dist(D):
    sec = D / LS
    if sec < 60: return f"{sec:.2f} LIGHT-SECONDS FROM EARTH"
    if sec < 3600: return f"{sec / 60:.1f} LIGHT-MINUTES FROM EARTH"
    if sec < 86400 * 2: return f"{sec / 3600:.1f} LIGHT-HOURS FROM EARTH"
    if D < 0.25: return f"{sec / 86400:.0f} LIGHT-DAYS FROM EARTH"
    if D < 10: return f"{D:.2f} LIGHT-YEARS FROM EARTH"
    if D < 1e6: return f"{int(round(D)):,} LIGHT-YEARS FROM EARTH"
    return f"{D / 1e6:.1f} MILLION LIGHT-YEARS FROM EARTH" if D < 1e7 else f"{D / 1e6:.0f} MILLION LIGHT-YEARS FROM EARTH"


# ------------------------------------------------------------------------------------ frame
def ring(ov, r, al, width=1, col=(170, 210, 255)):
    if r < 0.5 or r > 2600 or al <= 0.003: return
    ov.ellipse([CX - r, CY - r, CX + r, CY + r], outline=col + (int(255 * al),), width=width)


def render(fi):
    t = fi / FPS
    s = S[fi]; D = 10 ** s
    s_next = S[min(fi + 1, NF - 1)]
    cold = t < TL["cold_end"]
    frame = np.zeros((HEI, WID, 3), np.float32)
    ovim = Image.new("RGBA", (WID, HEI), (0, 0, 0, 0)); ov = ImageDraw.Draw(ovim)
    post = []          # things pasted after the overlay

    # --- distant sky
    a_in = 1 - sstep(3.9, 4.6, s); a_out = sstep(4.3, 5.0, s)
    if a_in > 0: frame += SKY_IN * a_in
    if a_out > 0: frame += SKY_OUT * a_out
    # --- galaxy plane
    a_gal = sstep(3.72, 4.35, s) * (1 - sstep(7.6, 8.2, s))
    if a_gal > 0.002:
        frame += galaxy_layer(D) * a_gal * 0.82
    # --- starfield stream (only between the stars: off inside the solar system and outside the galaxy)
    a_st = sstep(-0.6, 0.25, s) * (1 - sstep(3.75, 4.45, s))
    if a_st > 0.002:
        frame += bg_stream(s, s + 0.6 * (s_next - s) if not cold else s) * (a_st * 0.85)

    # --- Earth / Moon / Sun (main flight only)
    if not cold:
        # Sun
        so = OBJD["sun"]; pr = project(so["pos"], D)
        if pr:
            x, y, dist, dz = pr
            rpx = FOC * 696000 * KM / dist
            q = dist / so["d"]
            amp = float(np.clip(3.0 / q ** 0.5, 0.35, 3.0)) * (1 - 0.75 * sstep(-1.0, 1.0, s))
            glow(frame, x, y, (1.0, 0.93, 0.8), amp * 1.3, core=max(1.4, rpx), halo=14 + 40 / max(q, 0.5) ** 0.5, halo_amp=0.45, spikes=0.08 * amp)
            big_glow(frame, x, y, amp * 0.05)
        # Earth
        rpx = FOC * 6371 * KM / D
        a_e = 1.0
        if rpx >= 1.5:
            size = 2 * rpx * (EARTH.size[0] / 2) / EARTH_R
            spr = sprite_img(EARTH, size)
            paste(frame, spr, CX - spr.shape[1] / 2, CY - spr.shape[0] / 2)
        else:
            dl = LINES["dot"]
            a_dot = (0.95 - 0.35 * sstep(-7.5, -4.5, s)) * (1 - sstep(dl["end"] - 2.5, dl["end"] + 1.0, t))
            glow(frame, CX, CY, (0.55, 0.75, 1.0), a_dot * 1.2, core=1.2, halo=4.0, halo_amp=0.35)
        # Moon
        mo = OBJD["moon"]; pr = project(mo["pos"], D)
        if pr:
            x, y, dist, dz = pr
            mr = FOC * 1737 * KM / dist
            if mr >= 1.2:
                spr = sprite_img(MOON, 2 * mr * (MOON.size[0] / 2) / MOON_R)
                paste(frame, spr, x - spr.shape[1] / 2, y - spr.shape[0] / 2, float(1 - sstep(-6.6, -6.0, s)))
            else:
                glow(frame, x, y, (0.9, 0.9, 0.88), 0.5 * (1 - sstep(-6.6, -6.0, s)), core=0.8, halo=2, halo_amp=0.1)

    # --- hero stars, nebula, galaxies
    objs = [COLD] if cold else [o for o in OBJ if o["kind"] not in ("moon", "sun")]
    for o in objs:
        pr = project(o["pos"], D)
        if not pr: continue
        x, y, dist, dz = pr
        q = dist / o["d"]
        fade = float(1 - sstep(5.0, 11.0, q))
        if fade <= 0: continue
        col = o["col"]
        if o["kind"] == "star":
            amp = o["big"] * min(2.2, 1.1 / q) * fade * (0.6 if o.get("minor") else 1.0) * (1.7 if cold else 1.0)
            glow(frame, x, y, col, amp, core=1.0 + 0.5 * min(1, amp), halo=5 + 6 * min(1.5, amp), halo_amp=0.18,
                 spikes=0.04 * amp if o["big"] > 1.2 else 0)
        elif o["kind"] == "nebula":
            half = FOC * 60.0 / dist
            if half > 2:
                spr = sprite_img(ORION, 2 * half)
                add(frame, spr, x - spr.shape[1] / 2, y - spr.shape[0] / 2, 0.75 * fade)
        elif o["kind"] == "gc":
            glow(frame, x, y, (1.0, 0.9, 0.7), 0.5 * fade * a_gal, core=2.5, halo=30, halo_amp=0.25)
        elif o["kind"] == "lmc":
            half = FOC * 9000.0 / dist
            spr = sprite_img(LMCT, 2 * half, rotate=25, squash=0.75)
            add(frame, spr, x - spr.shape[1] / 2, y - spr.shape[0] / 2, 1.0 * fade)
        elif o["kind"] == "m31":
            half = FOC * 90000.0 / dist
            spr = sprite_img(M31T, 2 * half, rotate=38, squash=0.26)
            add(frame, spr, x - spr.shape[1] / 2, y - spr.shape[0] / 2, 1.15 * fade)
        # label
        if o.get("minor"):
            al = math.degrees(math.atan2(math.hypot(o["pos"][0], o["pos"][1]), dz))
            la = float(sstep(26, 21, al) * sstep(5.5, 8, al)) if not cold else 0
            if la > 0.01 and t > LINES["moon"]["start"] and 150 < y < HEI - 60: post.append((o, x, y, la))
        elif "show" in o:
            la = win(t, o["show"][0], o["show"][1], 0.6, 0.6)
            if la > 0.01: post.append((o, x, y, la))
    for o in OBJ:     # Moon and Sun labels
        if o["kind"] in ("moon", "sun") and not cold:
            pr = project(o["pos"], D)
            if pr:
                la = win(t, o["show"][0], o["show"][1], 0.5, 0.5)
                if la > 0.01: post.append((o, pr[0], pr[1], la))

    # --- radio bubble (R = 106 ly) and the 66-million-light-year shell
    for R, col, key in ((TL["radio_r"], (150, 200, 255), "radio"), (TL["dino_r"], (255, 190, 150), "dino")):
        if D > R:
            rr = FOC * math.tan(math.asin(R / D))
            a_r = 0.42 * (1 - sstep(math.log10(R) + 2.2, math.log10(R) + 3.0, s))
            ring(ov, rr, a_r, 2)
            ring(ov, rr + 3, a_r * 0.35, 3)
            if 60 < rr < 470:
                c = caption("OUR RADIO BUBBLE  ·  ≈ 106 LY" if key == "radio" else "LIGHT FROM 66 MILLION YEARS AGO", 13, (0.65, 0.78, 0.95) if key == "radio" else (0.95, 0.78, 0.65), 4)
                post.append(("cap", c, CX - c.shape[1] / 2, CY - rr - 24, a_r * 1.8))
        else:
            near = sstep(math.log10(R) - 0.2, math.log10(R), s)       # haze as we reach the shell
            frame += np.array(col, np.float32) / 255 * 0.05 * near
        # crossing flash
        if 1.0 < D / R < 1.05:
            frame += np.array(col, np.float32) / 255 * 0.10 * (1 - (D / R - 1) / 0.05)

    # --- centre marker for Earth once it is a dot
    if not cold:
        mk = win(t, LINES["dot"]["start"] + 1.0, TL["title"][0], 1.0, 1.0) * 0.55
        if mk > 0.01 and not (LINES["proxima"]["start"] < t < LINES["proxima"]["start"]):
            name = ("EARTH  ·  A PALE BLUE DOT" if D < 5e-3 else "EARTH") if D < 1 else ("SUN" if D < 3e5 else "MILKY WAY")
            r = 11
            ov.ellipse([CX - r, CY - r, CX + r, CY + r], outline=(200, 215, 240, int(255 * mk)), width=1)
            c = caption(name, 13, DIM, 4)
            post.append(("cap", c, CX - c.shape[1] / 2, CY + 18, mk))

    # --- labels (after all light)
    for item in post:
        if item[0] == "cap": continue
        o, x, y, la = item
        draw_label(frame, ov, o, x, y, la, inset=not o.get("minor"), t=t)
    # radio-bubble crossing / dino-shell crossing labels + their vignettes
    for key, vg, cap, lines_, anchor in (
        ("radio", "radio", "FIRST REGULAR RADIO BROADCASTS  ·  1920",
         [("THE EDGE OF OUR RADIO BUBBLE", FONT_L, 31, TXT, 6, 6), ("≈ 100 LIGHT-YEARS IN EVERY DIRECTION", FONT_L, 19, DIM, 3, 14),
          ("OUR EARLIEST BROADCASTS", FONT_L, 15, DIM, 4, 3), ("1920s", FONT_L, 40, GOLD, 3, 0)], (1150, 300)),
        ("dino", "dino", "THE CHICXULUB IMPACT  ·  66 MILLION YEARS AGO",
         [("66 MILLION LIGHT-YEARS", FONT_L, 31, TXT, 6, 6), ("THE LIGHT OF THE IMPACT IS HERE NOW", FONT_L, 19, DIM, 3, 14),
          ("SEES EARTH AS IT WAS", FONT_L, 15, DIM, 4, 3), ("66 MILLION YEARS AGO", FONT_L, 40, GOLD, 3, 0)], (1150, 300))):
        l = LINES[key]; nxt = TL["lines"][TL["order"].index(key) + 1]["start"]
        a = win(t, l["start"] - 0.3, nxt - 0.35)
        if a > 0.01:
            k = ("blk", key)
            if k not in CAP: CAP[k] = text_img(lines_, "left")
            paste(frame, CAP[k], anchor[0], anchor[1], a)
            draw_inset(frame, ov, vg, cap, "left", a * win(t, l["start"] + 0.4, nxt - 0.35, 0.7, 0.6))
    # bubble to scale, seen from the galaxy
    gl = LINES["gc"]
    a = win(t, gl["start"] + 4.0, gl["end"] + 1.2, 0.8, 0.6)
    if a > 0.01:
        ov.line([(CX - 14, CY - 14), (CX - 70, CY - 70), (CX - 90, CY - 70)], fill=(225, 230, 240, int(200 * a)), width=1)
        c = caption("OUR ENTIRE RADIO BUBBLE, TO SCALE: SMALLER THAN A PIXEL", 14, TXT * 0.9, 3, align="right")
        post.append(("cap", c, CX - 96 - c.shape[1], CY - 80, a))

    # --- top counter
    if not cold:
        ca = win(t, LINES["light"]["start"] + 1.0, TL["title"][0] - 0.5, 1.0, 1.0) * 0.9
        if ca > 0.01:
            c1 = caption("LIGHT ARRIVING HERE LEFT EARTH", 12, DIM, 5)
            c2 = text_img([(fmt_lookback(D), FONT_L, 26, TXT, 5, 0)], "center")
            c3 = text_img([(fmt_dist(D), FONT_L, 12, DIM, 4, 0)], "center")
            paste(frame, c1, CX - c1.shape[1] / 2, 38, ca)
            paste(frame, c2, CX - c2.shape[1] / 2, 58, ca)
            paste(frame, c3, CX - c3.shape[1] / 2, 98, ca * 0.9)

    # --- cards
    lc = TL["cards"][0]
    a = win(t, lc[0], lc[1], 0.8, 0.8)
    if a > 0.01:
        c = caption("LIGHT  ·  299,792 KM EVERY SECOND", 20, TXT, 6)
        post.append(("cap", c, CX - c.shape[1] / 2, 950, a))
    tc = TL["cards"][1]
    a = win(t, tc[0], tc[1], 0.9, 0.9)
    if a > 0.01:
        k = ("tele",)
        if k not in CAP:
            CAP[k] = text_img([("A TELESCOPE MIRROR AS WIDE AS THE EARTH  (12,742 KM)", FONT_L, 19, TXT, 4, 14),
                               ("FINEST DETAIL IT COULD SEE ON EARTH, FROM PROXIMA (4.2 LY):   ≈ 2 KM", FONT_L, 17, GOLD, 3, 8),
                               ("FROM VY CANIS MAJORIS (3,900 LY):   ≈ 2,000 KM", FONT_L, 17, GOLD, 3, 12),
                               ("DIFFRACTION LIMIT AT 550 NM  ·  AND IT WOULD CATCH ONLY A TRICKLE OF PHOTONS", FONT_L, 12, DIM, 3, 0)], "left")
        blk = CAP[k]
        bx = CX - blk.shape[1] / 2 + 70; by = 840
        er = 48
        ov.ellipse([bx - 150 - er, by + 52 - er, bx - 150 + er, by + 52 + er], outline=(230, 210, 160, int(220 * a)), width=2)
        espr = sprite_img(EARTH, 2 * 40 * (EARTH.size[0] / 2) / EARTH_R)
        post.append(("img", espr, bx - 150 - espr.shape[1] / 2, by + 52 - espr.shape[0] / 2, a * 0.9))
        post.append(("cap", blk, bx, by, a))

    # composite overlay (lines, rings)
    bb = ovim.getbbox()
    if bb:
        x0, y0, x1, y1 = bb
        ovn = np.asarray(ovim.crop(bb)).astype(np.float32) / 255
        al = ovn[..., 3:4]
        frame[y0:y1, x0:x1] = frame[y0:y1, x0:x1] * (1 - al) + ovn[..., :3] * al
    for item in post:
        if item[0] in ("cap", "img"):
            paste(frame, item[1], item[2], item[3], item[4])

    # --- end ripples, title card, fades
    e1 = LINES["end1"]
    a = win(t, e1["start"] - 1.0, TL["title"][0] + 0.5, 1.5, 1.5)
    if a > 0.01:
        rim = Image.new("RGBA", (WID, HEI), (0, 0, 0, 0)); rd = ImageDraw.Draw(rim)
        for k in range(7):
            ph = ((t - e1["start"] + 1.0) / 7.0 + k / 7) % 1.0
            r = 20 + ph ** 1.4 * 1150
            aa = a * 0.32 * (1 - ph) * sstep(0, 0.08, ph)
            rd.ellipse([CX - r, CY - r, CX + r, CY + r], outline=(230, 220, 200, int(255 * aa)), width=1)
        bb = rim.getbbox()
        if bb:
            x0, y0, x1, y1 = bb
            rn = np.asarray(rim.crop(bb)).astype(np.float32) / 255
            frame[y0:y1, x0:x1] = frame[y0:y1, x0:x1] * (1 - rn[..., 3:4]) + rn[..., :3] * rn[..., 3:4]
    # fade in at start, dip to black between cold open and Earth
    ce = TL["cold_end"]
    fade = sstep(0.0, 0.7, t) * (1 - sstep(ce - 0.7, ce, t) * (1 - sstep(ce + 0.05, ce + 1.2, t)))
    t0, t1 = TL["title"]
    fade *= 1 - sstep(t0 - 1.2, t0 + 0.3, t)
    frame *= fade
    if t > t0 - 0.2:
        a = win(t, t0 + 0.2, t1 + 5, 1.2, 0.1) * (1 - sstep(t1 - 0.9, t1 - 0.1, t))
        tt = caption("WHAT THEY SEE OF US", 60, TXT, 20, FONT_XL)
        paste(frame, tt, CX - tt.shape[1] / 2, CY - 70, a)
        b = win(t, t0 + 1.8, t1 + 5, 1.2, 0.1) * (1 - sstep(t1 - 0.9, t1 - 0.1, t))
        st = caption("PICK A STAR.  WHAT IS IT SEEING OF US RIGHT NOW?", 17, GOLD, 5)
        paste(frame, st, CX - st.shape[1] / 2, CY + 40, b)
    # soft shoulder instead of hard clip
    m = frame > 0.8
    if m.any():
        frame[m] = 0.8 + 0.2 * np.tanh((frame[m] - 0.8) / 0.2)
    return (np.clip(frame, 0, 1) * 255 + 0.5).astype(np.uint8)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=0); ap.add_argument("--end", type=int, default=NF)
    ap.add_argument("--out"); ap.add_argument("--stills"); ap.add_argument("--outdir", default=os.path.join(W_, "stills"))
    a = ap.parse_args()
    if a.stills:
        os.makedirs(a.outdir, exist_ok=True)
        for f in [int(x) for x in a.stills.split(",")]:
            Image.fromarray(render(f)).save(os.path.join(a.outdir, f"s_{f:05d}.png")); print("still", f, flush=True)
        sys.exit()
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{WID}x{HEI}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", a.out + ".part.mp4"]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    import time; t0 = time.time()
    for f in range(a.start, min(a.end, NF)):
        p.stdin.write(render(f).tobytes())
        if f % 48 == 0: print(f"frame {f}  {(time.time() - t0) / (f - a.start + 1):.2f}s/f", flush=True)
    p.stdin.close(); p.wait()
    os.replace(a.out + ".part.mp4", a.out)
    print("done", a.out)
