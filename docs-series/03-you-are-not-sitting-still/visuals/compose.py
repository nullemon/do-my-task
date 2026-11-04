"""
03 "YOU ARE NOT SITTING STILL" - frame compositor (numpy + PIL, /usr/bin/python3).

Builds every one of the 6480 frames (270 s @ 24 fps) from:
  * pre-baked 2D plates (gen_assets.py): room, window sky, horizon, CMB all-sky map
  * the Blender Earth loop (earth_blender.py, 288 RGBA frames)
  * light-weight 3D scenes projected here with a pinhole camera: solar-system orbits / helix (AU),
    the Milky Way disk + Sun orbit (kpc, textured plane from andromeda-doc ch2), the Local Group (kpc),
    and a procedural cosmic web (Mpc).  Lines are anti-aliased sample splats + soft glow.
  * all captions and live counters (Inter, drawn with PIL).
Timeline locked to the narration: ../audio/timeline.json.

Usage:
  python3 compose.py --stills 10,40,...        (seconds) -> prev/still_XXX.png
  python3 compose.py --part K --parts N        render part K of N to parts/part_KK.mp4 (skip if done)
"""
import os, sys, json, math, subprocess, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
S = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/03-you-are-not-sitting-still"
TEX = S + "/tex"
W, H, FPS = 1920, 1080, 24
TL = json.load(open(os.path.join(HERE, "..", "audio", "timeline.json")))
TOTAL = TL["total"]
NF = int(round(TOTAL * FPS))
LS = {l["id"]: l["start"] for l in TL["lines"]}
LE = {l["id"]: l["end"] for l in TL["lines"]}
SC = TL["scenes"]
V_CMB = 369.82          # km/s, Sun relative to the CMB (Planck 2018)
F32 = np.float32
FONT = "/usr/share/fonts/opentype/inter/"


# ------------------------------------------------------------------ timing helpers
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(a):
    a = clamp(a)
    return a * a * a * (a * (a * 6 - 15) + 10)


def smooth(a):
    a = clamp(a)
    return a * a * (3 - 2 * a)


def ramp(t, a, b):
    return ease((t - a) / max(1e-6, b - a))


def lerp(a, b, t):
    return a + (b - a) * t


def win(t, a, b, fi=0.8, fo=0.8):
    """1 inside [a, b], smooth fades of length fi before a... (fade-in starts at a) and fo after b."""
    if t < a or t > b + fo:
        return 0.0
    x = smooth((t - a) / fi) if fi > 0 else 1.0
    y = 1.0 - smooth((t - b) / fo) if t > b else 1.0
    return min(x, y)


# ------------------------------------------------------------------ image helpers
def load(name, mode=None):
    im = Image.open(f"{TEX}/{name}")
    if mode:
        im = im.convert(mode)
    return np.asarray(im).astype(F32) / 255.0


def boxblur(a, r, it=3):
    r = int(max(1, r))
    out = a
    for _ in range(it):
        for ax in (0, 1):
            pad = [(r + 1, r) if i == ax else (0, 0) for i in range(out.ndim)]
            c = np.cumsum(np.pad(out, pad, mode="constant"), axis=ax, dtype=F32)
            out = (c[2 * r + 1:] - c[:-2 * r - 1]) if ax == 0 else (c[:, 2 * r + 1:] - c[:, :-2 * r - 1])
            out = out / (2 * r + 1)
    return out


def glow(acc, r):
    """cheap wide blur of a HxW float map: downsample x4, box blur, bilinear upsample."""
    h, w = acc.shape
    sm = acc[:h - h % 4, :w - w % 4].reshape(h // 4, 4, w // 4, 4).mean((1, 3))
    sm = boxblur(sm, max(1, r / 4))
    return np.asarray(Image.fromarray(sm.astype(F32), "F").resize((w, h), Image.BILINEAR))


def to8(img):
    return Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))


def zoom_img(img, s, cx=W / 2, cy=H / 2):
    """scale an image about (cx, cy) by s (s<1 shrinks = pull back)."""
    if abs(s - 1) < 1e-4:
        return img
    im = to8(img)
    a = 1 / s
    im = im.transform((W, H), Image.AFFINE, (a, 0, cx - a * cx, 0, a, cy - a * cy), Image.BILINEAR)
    return np.asarray(im).astype(F32) / 255


# ------------------------------------------------------------------ text
class Fonts:
    cache = {}

    @classmethod
    def get(cls, name, size):
        k = (name, size)
        if k not in cls.cache:
            cls.cache[k] = ImageFont.truetype(FONT + name, size)
        return cls.cache[k]


_tcache = {}


def text_sprite(s, size, font="Inter-Light.otf", track=0.0):
    k = (s, size, font, track)
    if k in _tcache:
        return _tcache[k]
    f = Fonts.get(font, size)
    # width with tracking
    adv = [f.getlength(ch) for ch in s]
    wpx = int(sum(adv) + track * size * max(0, len(s) - 1)) + 8
    asc, desc = f.getmetrics()
    hpx = asc + desc + 6
    im = Image.new("L", (max(1, wpx), hpx), 0)
    d = ImageDraw.Draw(im)
    x = 2.0
    for ch, a in zip(s, adv):
        d.text((x, 2), ch, font=f, fill=255)
        x += a + track * size
    a = np.asarray(im).astype(F32) / 255
    _tcache[k] = (a, asc)
    if len(_tcache) > 4000:
        _tcache.clear()
    return a, asc


def put_text(img, s, x, y, size, col=(0.92, 0.91, 0.90), op=1.0, font="Inter-Light.otf", track=0.0,
             anchor="l", shadow=True):
    """y is the text baseline-ish top; anchor l/c/r horizontally."""
    if op <= 0.003 or not s:
        return 0
    a, asc = text_sprite(s, size, font, track)
    h, w = a.shape
    if anchor == "c":
        x = x - w / 2
    elif anchor == "r":
        x = x - w
    x, y = int(round(x)), int(round(y))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return w
    aa = a[y0 - y:y1 - y, x0 - x:x1 - x] * op
    reg = img[y0:y1, x0:x1]
    if shadow:   # soft dark halo for legibility over bright areas
        sh = boxblur(np.pad(aa, 6), 3, 2)[6:-6, 6:-6] * 0.55
        reg *= (1 - sh[..., None])
    reg[:] = reg * (1 - aa[..., None]) + np.array(col, F32) * aa[..., None]
    return w


def fmt_int(v):
    return f"{int(round(v)):,}"


# ------------------------------------------------------------------ camera / 3D
class Cam:
    def __init__(self, pos, target, fov_v=40.0, up=(0, 0, 1)):
        self.pos = np.array(pos, np.float64)
        f = np.array(target, np.float64) - self.pos
        f /= np.linalg.norm(f)
        r = np.cross(f, up)
        if np.linalg.norm(r) < 1e-6:
            r = np.cross(f, (0, 1, 0))
        r /= np.linalg.norm(r)
        u = np.cross(r, f)
        self.f, self.r, self.u = f, r, u
        self.fl = (H / 2) / math.tan(math.radians(fov_v) / 2)

    def project(self, P):
        d = np.asarray(P, np.float64) - self.pos
        z = d @ self.f
        zz = np.where(z > 1e-9, z, 1e-9)
        x = W / 2 + self.fl * (d @ self.r) / zz
        y = H / 2 - self.fl * (d @ self.u) / zz
        return x, y, z

    def dirs_project(self, D):
        z = D @ self.f
        zz = np.where(z > 1e-9, z, 1e-9)
        return W / 2 + self.fl * (D @ self.r) / zz, H / 2 - self.fl * (D @ self.u) / zz, z


def splat(acc, x, y, w):
    ok = (x >= 0) & (x < W - 1) & (y >= 0) & (y < H - 1) & (w > 0)
    x, y, w = x[ok], y[ok], w[ok]
    xi = x.astype(np.int64); yi = y.astype(np.int64)
    fx = (x - xi).astype(F32); fy = (y - yi).astype(F32)
    flat = acc.ravel()
    base = yi * W + xi
    np.add.at(flat, base, w * (1 - fx) * (1 - fy))
    np.add.at(flat, base + 1, w * fx * (1 - fy))
    np.add.at(flat, base + W, w * (1 - fx) * fy)
    np.add.at(flat, base + W + 1, w * fx * fy)


def polyline(acc, cam, P, wt=1.0, step=0.6, dash=None, near=1e-6):
    """anti-aliased polyline: resample the projected curve every `step` px, splat."""
    P = np.asarray(P, np.float64)
    x, y, z = cam.project(P)
    wt = np.broadcast_to(np.asarray(wt, np.float64), (len(P),)).copy()
    wt[z <= near] = 0
    seg = np.hypot(np.diff(x), np.diff(y))
    seg = np.where((z[1:] > near) & (z[:-1] > near) & (seg < 4000), seg, 0)
    s = np.concatenate([[0], np.cumsum(seg)])
    if s[-1] < 1:
        return
    n = int(s[-1] / step)
    if n > 400000:
        step = s[-1] / 400000; n = 400000
    sk = np.arange(n) * step
    xs = np.interp(sk, s, x); ys = np.interp(sk, s, y); ws = np.interp(sk, s, wt)
    if dash:
        on, period = dash
        ws = ws * ((sk % period) < on)
    splat(acc, xs, ys, (ws * step).astype(F32))


def add_dot(img, x, y, r, col, inten=1.0, halo=1.0):
    """bright point with gaussian core and soft halo."""
    R = int(r * 8 + 6)
    x0, x1 = int(x) - R, int(x) + R + 1
    y0, y1 = int(y) - R, int(y) + R + 1
    if x1 < 0 or y1 < 0 or x0 >= W or y0 >= H:
        return
    xs0, ys0 = max(0, x0), max(0, y0)
    xs1, ys1 = min(W, x1), min(H, y1)
    yy, xx = np.mgrid[ys0:ys1, xs0:xs1].astype(F32)
    d2 = (xx - x) ** 2 + (yy - y) ** 2
    g = np.exp(-d2 / (2 * r * r)) + halo * 0.12 * (r * r) / (d2 + r * r) * np.exp(-d2 / (2 * (R * 0.5) ** 2))
    img[ys0:ys1, xs0:xs1] += (g * inten)[..., None] * np.array(col, F32)


def colorize(img, acc, col, core=1.0, glow_r=0, glow_k=0.0):
    if glow_r and glow_k:
        img += (glow(acc, glow_r) * glow_k)[..., None] * np.array(col, F32)
    img += (np.minimum(acc * core, 1.6))[..., None] * np.array(col, F32)


# star sphere for all space scenes (directions), fixed seed
_rs = np.random.default_rng(7)
NST = 26000
_d = _rs.standard_normal((NST, 3)); _d /= np.linalg.norm(_d, axis=1, keepdims=True)
STAR_DIR = _d
STAR_B = np.minimum((_rs.pareto(1.6, NST) + 1) ** 1.25 * 0.10, 3.0).astype(F32)
_t = _rs.random(NST)
STAR_C = np.stack([np.interp(_t, [0, .4, 1], [0.78, 1.0, 1.0]), np.interp(_t, [0, .4, 1], [0.85, 0.96, 0.82]),
                   np.interp(_t, [0, .4, 1], [1.0, 0.95, 0.66])], 1).astype(F32)


def starfield(cam, k=1.0):
    img = np.zeros((H, W, 3), F32)
    x, y, z = cam.dirs_project(STAR_DIR)
    ok = z > 0.05
    for c in range(3):
        acc = np.zeros((H, W), F32)
        splat(acc, x[ok], y[ok], STAR_B[ok] * STAR_C[ok, c] * k)
        img[..., c] = acc
    img += glow(img.mean(2), 3)[..., None] * 0.5 * np.array([0.8, 0.85, 1.0], F32)
    return img


# ------------------------------------------------------------------ textured plane (galaxies)
class Tex:
    def __init__(self, name, sizes=(2048, 1024, 512, 256, 128)):
        im = Image.open(f"{TEX}/{name}").convert("RGB")
        self.levels = []
        for s in sizes:
            if s <= im.size[0]:
                self.levels.append(np.asarray(im.resize((s, s), Image.LANCZOS)).astype(F32) / 255)

    def level(self, px):
        for L in self.levels[::-1]:
            if L.shape[0] >= px:
                return L
        return self.levels[0]


def draw_plane(img, cam, tex, c, ua, va, half, gain=1.0, gamma_lin=True):
    """emissive square plane centre c, unit axes ua/va, half-size `half`, additive."""
    c = np.asarray(c, np.float64); ua = np.asarray(ua, np.float64); va = np.asarray(va, np.float64)
    n = np.cross(ua, va)
    corners = np.array([c + half * (sx * ua + sy * va) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    x, y, z = cam.project(corners)
    if (z <= 0).all():
        return
    if (z > 0).all():
        x0, x1 = int(max(0, x.min() - 2)), int(min(W, x.max() + 3))
        y0, y1 = int(max(0, y.min() - 2)), int(min(H, y.max() + 3))
        size_px = max(np.hypot(x[1] - x[0], y[1] - y[0]), np.hypot(x[3] - x[0], y[3] - y[0]))
    else:
        x0, x1, y0, y1 = 0, W, 0, H
        size_px = 4096
    if x1 <= x0 or y1 <= y0:
        return
    T = tex.level(size_px * 1.2)
    N = T.shape[0]
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float64)
    dx = (xx - W / 2) / cam.fl; dy = -(yy - H / 2) / cam.fl
    D = cam.f[None, None, :] + dx[..., None] * cam.r + dy[..., None] * cam.u
    denom = D @ n
    t = ((c - cam.pos) @ n) / np.where(np.abs(denom) < 1e-12, 1e-12, denom)
    Pw = cam.pos + t[..., None] * D
    q = Pw - c
    u = (q @ ua) / half; v = (q @ va) / half
    ok = (t > 0) & (np.abs(u) < 1) & (np.abs(v) < 1)
    if not ok.any():
        return
    fx = (u + 1) / 2 * (N - 1); fy = (1 - v) / 2 * (N - 1)
    fx = np.clip(fx, 0, N - 1.001); fy = np.clip(fy, 0, N - 1.001)
    ix = fx.astype(np.int64); iy = fy.astype(np.int64); ax = (fx - ix)[..., None]; ay = (fy - iy)[..., None]
    s = (T[iy, ix] * (1 - ax) * (1 - ay) + T[iy, ix + 1] * ax * (1 - ay) + T[iy + 1, ix] * (1 - ax) * ay
         + T[iy + 1, ix + 1] * ax * ay)
    # brighten when seen obliquely (more stars along the line of sight), capped
    view = abs(float(n @ cam.f))
    k = gain * min(2.2, 1 / max(0.25, view) ** 0.45)
    img[y0:y1, x0:x1] += (s * ok[..., None]).astype(F32) * k


# ================================================================== assets
print("loading assets", flush=True)
ROOM_BASE = load("room_base.png")
ROOM_WIN = load("room_win.png")
ROOM_RIM = load("room_rim.png")
HORIZON = load("horizon.png")
SKY = Image.open(f"{TEX}/sky_win.png").convert("RGB")
CMB = load("cmb_map.png")
CMB_APEX = [float(v) for v in open(f"{TEX}/cmb_apex.txt").read().split()]
PW, PH = ROOM_BASE.shape[1], ROOM_BASE.shape[0]
_g = np.linspace(0, 1, PH, dtype=F32)[:, None, None]
SKY_GRAD = np.array([0.020, 0.030, 0.070], F32) * (1 - _g) + np.array([0.040, 0.048, 0.090], F32) * _g
LONDON = {int(k): v for k, v in json.load(open(S + "/london_xy.json")).items()}
MW = Tex("ch2_mw.png")
M31 = Tex("ch2_m31.png", (2048, 1024, 512, 256, 128))
M33 = Tex("ch2_m33.png", (512, 256, 128))
LMC = Tex("ch2_lmc.png", (512, 256, 128))


# ================================================================== scene: ROOM
POLE = (1700.0, -420.0)   # celestial pole above the window (plate px)


def room(t, zoom, cx, cy, sky_rate=0.12, dark=1.0):
    ang = sky_rate * t      # degrees: gentle diurnal drift of the stars (time-lapse-ish, decorative)
    a = math.radians(ang)
    ca, sa = math.cos(a), math.sin(a)
    # output plate pixel p -> sky pixel: R(-a) (p - pole) + sky_pole
    spx, spy = 1500.0, 300.0
    A = (ca, sa, spx - ca * POLE[0] - sa * POLE[1], -sa, ca, spy + sa * POLE[0] - ca * POLE[1])
    sky = SKY.transform((PW, PH), Image.AFFINE, A, Image.BILINEAR)
    sk = np.asarray(sky).astype(F32) / 255 * 1.5 + SKY_GRAD
    sk = sk * (1 - HORIZON[..., 3:]) + HORIZON[..., :3]
    # town lights twinkle very slightly
    plate = ROOM_BASE + sk * ROOM_WIN[..., None] + ROOM_RIM
    plate *= dark
    im = to8(plate)
    # crop window of size (PW/zoom, PH/zoom) centred (cx, cy) in plate pixels -> W x H
    cw, ch = PW / zoom, PH / zoom
    x0 = clamp(cx - cw / 2, 0, PW - cw); y0 = clamp(cy - ch / 2, 0, PH - ch)
    sx, sy = cw / W, ch / H
    im = im.transform((W, H), Image.AFFINE, (sx, 0, x0, 0, sy, y0), Image.BICUBIC)
    return np.asarray(im).astype(F32) / 255


# ================================================================== scene: EARTH
E0, E1 = SC["earth"]
EARTH_PHASE_T = LS["l06"] + 4.0      # London faces the camera at this time


def earth_idx(t):
    return int(math.floor((t - EARTH_PHASE_T) * FPS)) % 288 + 1


_ecache = {}


def earth_frame(i):
    if i not in _ecache:
        if len(_ecache) > 6:
            _ecache.clear()
        _ecache[i] = np.asarray(Image.open(f"{S}/earth_frames/e_{i:04d}.png").convert("RGBA")).astype(F32) / 255
    return _ecache[i]


EARTH_CAM = Cam((0, 0, 0), (0, 0, 1), 40)   # only used for the star sphere orientation


def scene_earth(t):
    cam = Cam((0, 0, 0), (1, -0.25, 0.12), 38)
    img = starfield(cam, 0.8)
    e = earth_frame(earth_idx(t))
    img = img * (1 - e[..., 3:]) + e[..., :3]
    lt = t - E0
    # labels
    o = win(t, LS["l05"] + 0.3, E1 - 2.5)
    if o > 0:
        put_text(img, "EQUATOR", 1690, 600, 17, (1.0, 0.86, 0.66), o, "Inter-Regular.otf", 0.25)
        put_text(img, "≈ 1,670 km/h", 1690, 624, 30, (1.0, 0.92, 0.82), o)
    i = earth_idx(t)
    lx, ly, vis = LONDON[i]
    o = win(t, LS["l06"] + 3.4, E1 - 2.5) * smooth((vis - 0.15) / 0.25)
    if o > 0:
        put_text(img, "LONDON  51.5° N", lx + 22, ly - 52, 17, (0.86, 0.80, 1.0), o, "Inter-Regular.otf", 0.25)
        put_text(img, "≈ 1,040 km/h", lx + 22, ly - 28, 30, (0.95, 0.93, 1.0), o)
    o = win(t, LS["l06"] + 7.4, E1 - 2.5)
    if o > 0:
        put_text(img, "POLES  ≈ 0 km/h", 1228, 72, 17, (0.88, 0.88, 0.92), o, "Inter-Regular.otf", 0.25, "c")
    o = win(t, LS["l06"] + 0.6, E1 - 2.5)
    if o > 0:
        put_text(img, "SPEED  =  1,670 km/h  ×  cos(latitude)", 1228, 1000, 24, (0.9, 0.9, 0.92), o, track=0.08, anchor="c")
    o = win(t, E0 + 2.5, E1 - 2.5)
    put_text(img, "TIME-LAPSE  ·  ONE DAY IN 12 SECONDS", W - 70, 60, 15, (0.7, 0.7, 0.75), 0.8 * o,
             "Inter-Regular.otf", 0.3, "r")
    return img


# ================================================================== scene: ORBIT + HELIX (units: AU, years)
O0, O1 = SC["orbit"][0], SC["helix"][1]
PLANETS = [  # name, a (AU), period (yr), colour, dot radius px, phase
    ("MERCURY", 0.387, 0.2408, (0.85, 0.80, 0.75), 1.6, 1.1),
    ("VENUS", 0.723, 0.6152, (1.0, 0.90, 0.72), 2.0, 2.4),
    ("EARTH", 1.000, 1.0000, (0.45, 0.70, 1.0), 2.4, 4.2),
    ("MARS", 1.524, 1.8808, (1.0, 0.55, 0.38), 1.9, 0.3),
]
TILT = math.radians(60.0)
DIR = np.array([math.cos(TILT), 0.0, math.sin(TILT)])     # Sun's galactic path, 60 deg to the ecliptic (xy) plane
V_SUN = 230.0 / 29.78 * 2 * math.pi                       # AU per year (~48.5)
T_MOVE0 = LS["l09"] + 1.5                                 # Sun "starts" moving (frame change) ...
T_MOVE1 = T_MOVE0 + 7.0                                   # ... at full speed


def yr(t):          # simulated years since the orbit scene began (time-lapse: 1 year in 10 s)
    return (t - O0) / 10.0


def sun_s(t):       # distance travelled by the Sun along DIR (AU) in the galaxy frame, ramped in
    # integral of V_SUN * ramp over simulated time
    # the Sun moves steadily the whole time; the camera simply rides along with it until the trails appear
    return V_SUN * yr(t)


def planet_pos(p, y):
    _, a, per, _, _, ph = p
    th = ph + 2 * math.pi * y / per
    return np.stack([a * np.cos(th), a * np.sin(th), np.zeros_like(th)], -1)


def scene_solar(t):
    y = yr(t)
    s_now = sun_s(t)
    sun = DIR * s_now
    # camera: start above the ecliptic (orbit view) -> side-on to the path, pulling back
    k = ramp(t, LS["l09"] + 0.5, LS["l10"] + 6.0)
    k2 = ramp(t, LS["l10"] - 1.0, O1 - 1.0)
    az = math.radians(lerp(-70 + 8 * (t - O0) / 20, 90, k))
    el = math.radians(lerp(30, 12, k))
    dist = lerp(lerp(4.6, 3.6, ramp(t, O0, O0 + 18)), 14.0, k) * lerp(1.0, 5.2, k2)
    az0 = math.radians(-70 + 8 * (t - O0) / 20)
    off0 = np.array([math.cos(math.radians(30)) * math.cos(az0), math.cos(math.radians(30)) * math.sin(az0), math.sin(math.radians(30))])
    U = np.array([-math.sin(TILT), 0.0, math.cos(TILT)])          # perpendicular to the path, in the x-z plane
    el1 = math.radians(14)
    off1 = math.cos(el1) * np.array([0.0, -1.0, 0.0]) + math.sin(el1) * U
    off = off0 * (1 - k) + off1 * k
    off /= np.linalg.norm(off)
    up = np.array([0, 0, 1.0]) * (1 - k) + U * k
    target = sun - DIR * lerp(0, 0.30, k) * dist
    cam = Cam(target + off * dist, target, 42, up=up / np.linalg.norm(up))
    img = starfield(cam, 0.75)
    # heliocentric orbit rings (always drawn around the current Sun position)
    ring_o = 1 - 0.65 * k
    acc = np.zeros((H, W), F32)
    th = np.linspace(0, 2 * math.pi, 721)
    for p in PLANETS:
        P = sun + np.stack([p[1] * np.cos(th), p[1] * np.sin(th), 0 * th], -1)
        polyline(acc, cam, P, 0.30 if p[0] != "EARTH" else 0.55)
    colorize(img, acc, (0.65, 0.70, 0.85), ring_o, 6, 0.3 * ring_o)
    # galaxy-frame trails (only once the Sun moves): past positions over the last ~6 years
    if t > T_MOVE0:
        ty = np.linspace(max(0, y - 6.0), y, 3000)
        # sun position along the trail: s(t') ; precompute on the time grid
        tt = O0 + ty * 10.0
        s_tr = V_SUN * ty
        fade = np.clip((ty - (y - 6.0)) / 2.0, 0, 1) * np.clip((tt - T_MOVE0) / 1.5, 0, 1)
        for p in PLANETS:
            acc = np.zeros((H, W), F32)
            P = DIR[None, :] * s_tr[:, None] + planet_pos(p, ty)
            polyline(acc, cam, P, fade * (0.9 if p[0] == "EARTH" else 0.45))
            colorize(img, acc, p[3], 1.0, 8, 0.45)
        # the Sun's own path (dashed ahead + solid behind)
        acc = np.zeros((H, W), F32)
        polyline(acc, cam, np.array([sun - DIR * 400, sun]), 0.35)
        polyline(acc, cam, np.array([sun, sun + DIR * 400]), 0.30, dash=(10, 22))
        colorize(img, acc, (1.0, 0.85, 0.6), 1.0, 0, 0)
    # sun + planets
    sx, sy, sz = cam.project(sun[None])
    rpx = max(3.0, cam.fl * 0.035 / max(sz[0], 1e-3))
    add_dot(img, sx[0], sy[0], rpx, (1.0, 0.86, 0.6), 1.6, 2.5)
    for p in PLANETS:
        P = sun + planet_pos(p, np.array([y]))
        px, py, pz = cam.project(P)
        add_dot(img, px[0], py[0], p[4], p[3], 1.4, 1.0)
        if p[0] == "EARTH":
            ex, ey = px[0], py[0]
    # labels
    o = win(t, LS["l07"] + 1.0, LS["l09"] + 2.0) * (1 - k)
    if o > 0:
        put_text(img, "EARTH", ex + 16, ey - 36, 16, (0.7, 0.82, 1.0), o, "Inter-Regular.otf", 0.3)
        put_text(img, "29.8 km/s", ex + 16, ey - 16, 24, (0.9, 0.94, 1.0), o)
    o = win(t, LS["l07"] + 1.0, LS["l09"] - 1.0)
    put_text(img, "TIME-LAPSE  ·  ONE YEAR IN 10 SECONDS", W - 70, 60, 15, (0.7, 0.7, 0.75), 0.8 * o,
             "Inter-Regular.otf", 0.3, "r")
    o = win(t, T_MOVE0 + 1.0, O1 - 2.0)
    put_text(img, "SEEN FROM THE GALAXY'S FRAME  ·  PATH SHAPE TO SCALE  ·  SUN & PLANETS ENLARGED", W - 70, 60, 15,
             (0.7, 0.7, 0.75), 0.8 * o, "Inter-Regular.otf", 0.25, "r")
    o = win(t, T_MOVE0 + 3.0, O1 - 2.0)
    if o > 0:
        # label at a point ahead on the Sun's path
        ax_, ay_, az_ = cam.project(sun[None])
        put_text(img, "THE SUN'S PATH AROUND THE GALAXY  →", min(ax_[0] - 360, W - 520), ay_[0] + 40, 15, (1.0, 0.88, 0.7), o,
                 "Inter-Regular.otf", 0.25)
    # the 60 degree angle between the path and the planets' plane
    o = win(t, LS["l10"] + 0.3, LS["l10"] + 9.0, 1.0, 1.2)
    if o > 0:
        acc = np.zeros((H, W), F32)
        R = 2.1
        polyline(acc, cam, np.array([sun, sun + np.array([1, 0, 0]) * R * 1.25]), 0.6 * o, dash=(5, 9))
        a = np.linspace(0, TILT, 80)
        polyline(acc, cam, sun + R * np.stack([np.cos(a), 0 * a, np.sin(a)], -1), 0.7 * o)
        colorize(img, acc, (0.85, 0.78, 1.0), 1.0, 0, 0)
        mid = sun + (R + 0.35) * np.array([math.cos(TILT / 2), 0, math.sin(TILT / 2)])
        mx, my, _ = cam.project(mid[None])
        put_text(img, "≈ 60°", mx[0] + 6, my[0] - 14, 26, (0.9, 0.86, 1.0), o)
    o = win(t, LS["l10"] + 9.4, O1 - 2.2, 1.0, 1.0)
    if o > 0:
        put_text(img, "EACH YEAR THE SUN TRAVELS ≈ 48 AU  ·  EARTH'S ORBIT IS 2 AU WIDE", W / 2 + 180, 990, 19,
                 (0.88, 0.88, 0.92), o, "Inter-Light.otf", 0.12, "c")
    return img


# ================================================================== scene: GALAXY (units: kpc, Myr)
G0, G1 = SC["galaxy"]
R_SUN = 8.2
HALF_MW = 18.0
MYR_PER_S = 1.0
PHI0 = math.radians(-118.0)            # Sun's azimuth on the texture at the start of the scene
BOB_A_TRUE = 0.08                      # kpc (~80 pc) amplitude of the vertical oscillation
BOB_X = 10.0                           # exaggeration shown on screen
BOB_P = 64.0                           # Myr full period


def sun_gal(t):
    myr = (t - G0) * MYR_PER_S
    phi = PHI0 - 2 * math.pi * myr / 230.0          # clockwise seen from the north galactic pole
    zb = BOB_A_TRUE * BOB_X * math.sin(2 * math.pi * (myr + 6) / BOB_P) * ramp(t, LS["l14"] - 1, LS["l14"] + 2)
    return np.array([R_SUN * math.cos(phi), R_SUN * math.sin(phi), zb]), phi, myr


def scene_galaxy(t):
    sun, phi, myr = sun_gal(t)
    k = ramp(t, G0, LS["l12"] + 4.0)                 # pull back from the Sun to the whole disk
    kb = ramp(t, LS["l14"] - 1.5, LS["l14"] + 4.5)   # tilt to nearly edge-on for the bobbing
    dist = lerp(7.0, 46.0, k) * lerp(1.0, 0.82, kb)
    el = math.radians(lerp(lerp(70, 52, k), 7.0, kb))
    az = phi - math.radians(lerp(40, 75, k)) - 0.04 * (t - G0) * 0.15
    tgt = sun * (1 - k) + np.array([0.0, 0.0, 0.0]) * k
    tgt = tgt * (1 - kb) + (sun * 0.35) * kb
    off = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
    cam = Cam(tgt + off * dist, tgt, 44)
    img = starfield(cam, 0.7)
    draw_plane(img, cam, MW, (0, 0, 0), (1, 0, 0), (0, 1, 0), HALF_MW, lerp(0.45, 0.95, k))
    # Sun's orbit circle (dashed) + bobbing wave (exaggerated)
    th = np.linspace(0, 2 * math.pi, 1500)
    acc = np.zeros((H, W), F32)
    ring = np.stack([R_SUN * np.cos(th), R_SUN * np.sin(th), 0 * th], -1)
    polyline(acc, cam, ring, 0.55 * (1 - 0.6 * kb), dash=(9, 14))
    colorize(img, acc, (1.0, 0.85, 0.6), 1.0, 0, 0)
    if kb > 0:
        acc = np.zeros((H, W), F32)
        dphi = (th - phi + math.pi) % (2 * math.pi) - math.pi     # angle ahead (-) / behind (+) of the Sun
        myr_rel = dphi / (2 * math.pi) * 230.0                      # Myr in the past (+) of the current point
        z = BOB_A_TRUE * BOB_X * np.sin(2 * math.pi * (myr - myr_rel + 6) / BOB_P)
        wave = np.stack([R_SUN * np.cos(th), R_SUN * np.sin(th), z], -1)
        polyline(acc, cam, wave, 0.9 * kb)
        colorize(img, acc, (0.85, 0.78, 1.0), 1.0, 8, 0.4)
    sx, sy, sz = cam.project(sun[None])
    add_dot(img, sx[0], sy[0], 3.2, (1.0, 0.9, 0.7), 1.8, 2.0)
    o = win(t, G0 + 1.5, G1 - 2.0)
    if o > 0:
        put_text(img, "SUN", sx[0] + 18, sy[0] - 44, 16, (1.0, 0.88, 0.7), o, "Inter-Regular.otf", 0.3)
        put_text(img, "≈ 230 km/s", sx[0] + 18, sy[0] - 22, 24, (1.0, 0.95, 0.88), o)
    gx, gy, _ = cam.project(np.array([[0, 0, 0.0]]))
    o = win(t, LS["l11"] + 2.0, G1 - 2.0) * k
    put_text(img, "GALACTIC CENTRE", gx[0], gy[0] + 74, 15, (0.85, 0.82, 0.78), 0.8 * o, "Inter-Regular.otf", 0.3, "c")
    o = win(t, G0 + 2.5, G1 - 2.0)
    put_text(img, "MILKY WAY (ILLUSTRATION)  ·  TIME-LAPSE ≈ 1 MILLION YEARS PER SECOND", W - 70, 60, 15,
             (0.7, 0.7, 0.75), 0.8 * o, "Inter-Regular.otf", 0.25, "r")
    o = win(t, LS["l13"] + 0.3, LS["l13"] + 4.9)
    if o > 0:
        put_text(img, "ONE LAP ≈ 230 MILLION YEARS", W / 2 + 200, 940, 30, (0.95, 0.94, 0.92), o, anchor="c", track=0.05)
        put_text(img, "ESTIMATES RANGE FROM ABOUT 225 TO 250 MILLION", W / 2 + 200, 984, 16, (0.75, 0.75, 0.8), o,
                 "Inter-Regular.otf", 0.25, "c")
    o = win(t, LS["l13"] + 6.0, LS["l14"] - 1.0)
    if o > 0:
        put_text(img, "~230 MILLION YEARS AGO: THE FIRST DINOSAURS", W / 2 + 200, 940, 30, (0.95, 0.94, 0.92), o,
                 anchor="c", track=0.05)
        put_text(img, "LATE TRIASSIC", W / 2 + 200, 984, 16, (0.75, 0.75, 0.8), o, "Inter-Regular.otf", 0.3, "c")
    o = win(t, LS["l14"] + 1.0, G1 - 1.8)
    if o > 0:
        put_text(img, "UP AND DOWN THROUGH THE DISK  ·  CROSSING IT EVERY ~30 MILLION YEARS", W / 2 + 200, 940, 22,
                 (0.92, 0.9, 1.0), o, anchor="c", track=0.06)
        put_text(img, "VERTICAL MOTION EXAGGERATED ×10  (REAL SWING ≈ ±80 PARSECS)", W / 2 + 200, 980, 15,
                 (0.72, 0.72, 0.78), o, "Inter-Regular.otf", 0.25, "c")
    return img


# ================================================================== scene: COSMOS (Local Group kpc -> cosmic web Mpc)
C0, C1 = SC["cosmos"]
GSC = 3.0     # galaxy disks drawn 2x true size so they are visible (labelled)
LG = dict(
    mw=dict(p=np.array([0.0, 0.0, 0.0]), ua=(1, 0, 0), va=(0, 0.5, 0.866), half=HALF_MW * GSC, tex=MW, g=0.9, name="MILKY WAY"),
    m31=dict(p=np.array([770.0, 60.0, -80.0]), ua=(0.2, 0.98, 0.0), va=(-0.3, 0.06, 0.95), half=24.0 * GSC, tex=M31, g=0.9,
             name="ANDROMEDA"),
    m33=dict(p=np.array([805.0, -205.0, -35.0]), ua=(0.7, 0.7, 0.1), va=(-0.5, 0.5, 0.7), half=9.0 * GSC, tex=M33, g=0.8,
             name="TRIANGULUM"),
    lmc=dict(p=np.array([-24.0, -38.0, -24.0]), ua=(1, 0, 0), va=(0, 0.6, 0.8), half=5.0 * GSC, tex=LMC, g=0.8, name=""),
)
T_WEB = LS["l18"] - 1.0


def gal_dir(l, b, d):
    l, b = math.radians(l), math.radians(b)
    return np.array([math.cos(b) * math.cos(l), math.cos(b) * math.sin(l), math.sin(b)]) * d


GA = gal_dir(315, 2, 68.0)          # Great Attractor region (Norma cluster ~68 Mpc)
SHAP = gal_dir(312, 31, 200.0)      # Shapley Supercluster (~200 Mpc)
LG_V = gal_dir(276, 30, 1.0)        # Local Group motion relative to the CMB


def make_web():
    r = np.random.default_rng(5)
    nodes = r.uniform(-320, 320, (150, 3))
    mass = r.pareto(1.5, 150) + 0.4
    nodes = np.vstack([nodes, GA, SHAP, SHAP + gal_dir(300, 25, 30), np.zeros(3)])
    mass = np.concatenate([mass, [9.0, 22.0, 6.0, 0.6]])
    pts = []; br = []
    # filaments to 3 nearest neighbours
    for i in range(len(nodes)):
        d = np.linalg.norm(nodes - nodes[i], axis=1)
        for j in np.argsort(d)[1:4]:
            n = int(min(900, d[j] * 3))
            u = r.random(n)[:, None]
            p = nodes[i] * (1 - u) + nodes[j] * u + r.standard_normal((n, 3)) * 3.0
            pts.append(p); br.append(np.full(n, 0.35))
    for i in range(len(nodes)):
        n = int(160 * mass[i])
        p = nodes[i] + r.standard_normal((n, 3)) * (2.5 + 1.5 * mass[i] ** 0.5)
        pts.append(p); br.append(np.full(n, 0.6))
    P = np.vstack(pts); B = np.concatenate(br) * (0.5 + r.random(len(np.concatenate(br))))
    return P, B.astype(F32)


WEB_P, WEB_B = make_web()


def scene_cosmos(t):
    if t < T_WEB + 1.6:
        a = local_group(t)
        if t < T_WEB:
            return a
        b = cosmic_web(t)
        x = smooth((t - T_WEB) / 1.6)
        return a * (1 - x) + b * x
    return cosmic_web(t)


def local_group(t):
    k = ramp(t, C0, LS["l16"])
    mid = np.array([420.0, -40.0, -40.0])
    tgt = lerp(np.array([0.0, 0, 0]), mid, k)
    d = lerp(180.0, 1150.0, k) * lerp(1, 1.10, ramp(t, LS["l16"], T_WEB))
    az = math.radians(-100 + 18 * (t - C0) / 30.0); el = math.radians(lerp(35, 28, k))
    off = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
    cam0 = Cam(tgt + off * d, tgt, 42)
    shift = cam0.r * 0.17 * d * k            # keep the galaxies left of the CMB map
    cam = Cam(tgt + off * d + shift, tgt + shift, 42)
    img = starfield(cam, 0.6)
    dim = 1 - 0.35 * win(t, LS["l16"] - 0.5, T_WEB - 1.5, 1.2, 1.2)
    for g in LG.values():
        draw_plane(img, cam, g["tex"], g["p"], np.array(g["ua"], float) / np.linalg.norm(g["ua"]),
                   np.array(g["va"], float) / np.linalg.norm(g["va"]), g["half"], g["g"] * dim)
    o = win(t, C0 + 3.0, T_WEB - 0.5) * (0.4 + 0.6 * k)
    for g in LG.values():
        if not g["name"]:
            continue
        x, y, z = cam.project(g["p"][None])
        put_text(img, g["name"], x[0], y[0] + 38 + g["half"] * cam.fl / max(z[0], 1) * 0.25, 15, (0.85, 0.85, 0.9), o * dim,
                 "Inter-Regular.otf", 0.3, "c")
    o = win(t, C0 + 2.0, T_WEB - 0.5)
    put_text(img, "THE LOCAL GROUP  ·  GALAXIES DRAWN 3× TRUE SIZE", W - 70, 60, 15, (0.7, 0.7, 0.75), 0.8 * o,
             "Inter-Regular.otf", 0.25, "r")
    # the CMB all-sky map
    o = win(t, LS["l16"] + 0.5, T_WEB - 1.2, 1.4, 1.2)
    if o > 0:
        mw, mh = 600, 300
        cm = np.asarray(to8(CMB[..., :3]).resize((mw, mh), Image.LANCZOS)).astype(F32) / 255
        al = np.asarray(Image.fromarray((CMB[..., 3] * 255).astype(np.uint8)).resize((mw, mh), Image.LANCZOS)).astype(F32) / 255
        x0, y0 = 1250, 210
        reg = img[y0:y0 + mh, x0:x0 + mw]
        reg[:] = reg * (1 - al[..., None] * o) + cm * al[..., None] * o
        ax = x0 + CMB_APEX[0] * mw / CMB.shape[1]; ay = y0 + CMB_APEX[1] * mh / CMB.shape[0]
        acc = np.zeros((H, W), F32)
        cth = np.linspace(0, 2 * math.pi, 200)
        cam2 = None
        xs = ax + 16 * np.cos(cth); ys = ay + 16 * np.sin(cth)
        splat(acc, xs, ys, np.full(200, 0.9 * o, F32))
        img += np.minimum(acc, 1)[..., None] * np.array([1, 1, 1], F32)
        put_text(img, "COSMIC MICROWAVE BACKGROUND  ·  WHOLE SKY", x0 + mw / 2, y0 - 46, 17, (0.92, 0.9, 0.9), o,
                 "Inter-Regular.otf", 0.25, "c")
        o2 = o * win(t, LS["l16"] + 6.5, T_WEB, 1.0, 1.0)
        put_text(img, "WE'RE HEADING THIS WAY", ax, ay + 24, 15, (1.0, 0.95, 0.85), o2,
                 "Inter-Regular.otf", 0.2, "c")
        put_text(img, "≈ 370 km/s", ax, ay + 46, 22, (1.0, 0.95, 0.85), o2, "Inter-Light.otf", 0.02, "c")
        put_text(img, "≈ 0.1% WARMER AHEAD, COOLER BEHIND (COLOURS EXAGGERATED)", x0 + mw / 2, y0 + mh + 18, 15,
                 (0.75, 0.75, 0.8), o2, "Inter-Regular.otf", 0.22, "c")
    o = win(t, LS["l17"] + 0.3, T_WEB - 0.8)
    if o > 0:
        put_text(img, "THE SPEEDS POINT IN DIFFERENT DIRECTIONS  ·  THEY DON'T SIMPLY ADD", W / 2 + 180, 1000, 17,
                 (0.85, 0.85, 0.9), o, "Inter-Regular.otf", 0.2, "c")
    return img


def cosmic_web(t):
    k = ramp(t, T_WEB, T_WEB + 9.0)
    dist = lerp(6.0, 520.0, k ** 1.6)
    tgt = lerp(np.zeros(3), (GA + SHAP) * 0.35, ramp(t, T_WEB + 2, T_WEB + 12))
    nrm = np.cross(GA, SHAP); nrm /= np.linalg.norm(nrm)
    a = math.radians(-12 + 16 * (t - T_WEB) / 20.0)          # slow drift around the vertical
    ca, sa = math.cos(a), math.sin(a)
    off = np.array([ca * nrm[0] - sa * nrm[1], sa * nrm[0] + ca * nrm[1], nrm[2]])
    off = off + np.array([0, 0, 0.25]); off /= np.linalg.norm(off)
    cam = Cam(tgt + off * dist, tgt, 46)
    img = starfield(cam, 0.35 * (1 - k))
    x, y, z = cam.project(WEB_P)
    ok = z > 0.5
    b = WEB_B[ok] * np.clip(60.0 / z[ok], 0.05, 3.0) ** 0.6 * 0.5
    acc = np.zeros((H, W), F32)
    splat(acc, x[ok], y[ok], b.astype(F32))
    colorize(img, acc, (0.72, 0.76, 1.0), 1.5, 10, 1.4)
    colorize(img, acc, (1.0, 0.85, 0.7), 0.25, 0, 0)
    # Local Group marker + motion arrow
    lx, ly, lz = cam.project(np.zeros((1, 3)))
    add_dot(img, lx[0], ly[0], 2.6, (1.0, 0.95, 0.85), 1.6, 1.5)
    o = win(t, T_WEB + 1.0, C1 - 2.0)
    put_text(img, "LOCAL GROUP  ·  US", lx[0] - 16, ly[0] - 8, 15, (1.0, 0.95, 0.88), o, "Inter-Regular.otf", 0.3, "r")
    oa = win(t, T_WEB + 4.0, C1 - 2.0, 1.4)
    if oa > 0:
        L = 110.0 * ramp(t, T_WEB + 4.0, T_WEB + 7.0)
        acc = np.zeros((H, W), F32)
        tip = LG_V * L
        polyline(acc, cam, np.array([np.zeros(3), tip]), 1.4 * oa)
        tx, ty, _ = cam.project(np.array([tip]))
        hx, hy, _ = cam.project(np.array([LG_V * L * 0.86]))
        dx, dy = tx[0] - hx[0], ty[0] - hy[0]
        nrm = math.hypot(dx, dy) + 1e-6
        dx, dy = dx / nrm, dy / nrm
        for sgn in (1, -1):
            bx = tx[0] - 16 * dx + sgn * 7 * dy; by = ty[0] - 16 * dy - sgn * 7 * dx
            s_ = np.linspace(0, 1, 40)
            splat(acc, tx[0] + (bx - tx[0]) * s_, ty[0] + (by - ty[0]) * s_, np.full(40, 1.0 * oa, F32))
        colorize(img, acc, (1.0, 0.9, 0.7), 1.0, 4, 0.5)
        put_text(img, "≈ 600 km/s", tx[0] + 14, ty[0] - 14, 22, (1.0, 0.94, 0.85), oa)
    for P, nm, sub in ((GA, "GREAT ATTRACTOR", "≈ 200 MILLION LIGHT-YEARS"), (SHAP, "SHAPLEY SUPERCLUSTER", "≈ 650 MILLION LIGHT-YEARS")):
        o = win(t, LS["l18"] + (9.0 if nm[0] == "G" else 12.0), C1 - 2.0)
        if o > 0:
            px, py, pz = cam.project(P[None])
            dy = 30
            put_text(img, nm, px[0], py[0] + dy, 16, (0.9, 0.9, 1.0), o, "Inter-Regular.otf", 0.3, "c")
            put_text(img, sub, px[0], py[0] + dy + 22, 14, (0.7, 0.7, 0.8), o, "Inter-Regular.otf", 0.25, "c")
    o = win(t, T_WEB + 3.0, C1 - 2.0)
    put_text(img, "ILLUSTRATIVE MAP OF GALAXIES  ·  DIRECTIONS APPROXIMATE", W - 70, 60, 15, (0.7, 0.7, 0.75), 0.8 * o,
             "Inter-Regular.otf", 0.25, "r")
    return img


# ================================================================== scenes: WHY / END (room)
WY0, WY1 = SC["why"]
N0, N1 = SC["end"]


def scene_why(t):
    z = lerp(1.28, 1.36, ramp(t, WY0, WY1))
    img = room(t, z, 1060, 660)
    caps = [
        (LS["l20"] + 0.2, LS["l21"] - 0.6, "YOU FEEL CHANGES IN MOTION  —  NOT MOTION ITSELF", ""),
        (LS["l21"] + 3.2, LS["l21"] + 7.6, "GALILEO  ·  1632", "A SHIP ON CALM WATER: BELOW DECK, NOTHING SHOWS YOU'RE MOVING"),
        (LS["l21"] + 8.2, LS["l22"] - 0.6, "NEWTON'S FIRST LAW  ·  1687", "STEADY MOTION NEEDS NO FORCE, AND YOU FEEL NONE"),
        (LS["l22"] + 0.2, WY1 - 2.0, "THE CURVES ARE GENTLE", "EARTH'S SPIN TUGS YOU AT ≈ 0.03 m/s²  ·  ABOUT 0.3% OF GRAVITY"),
    ]
    for a, b, big, small in caps:
        o = win(t, a, b, 0.9, 0.9)
        if o > 0:
            put_text(img, big, 1340, 858, 28, (0.95, 0.94, 0.92), o, "Inter-Light.otf", 0.10, "c")
            put_text(img, small, 1340, 902, 15, (0.76, 0.76, 0.82), o, "Inter-Regular.otf", 0.22, "c")
    return img


def scene_end(t):
    z = lerp(1.36, 1.02, ramp(t, N0, N1 - 1.0))
    dk = 1 - 0.45 * ramp(t, LS["l23"] - 0.5, LS["l23"] + 2.0)
    img = room(t, z, 1180, 640, dark=dk)
    return img


# ================================================================== overlays: counters & speed stack
STACK = [  # appear time, label, value(final), formatter, sub
    (LS["l05"] + 0.6, "EARTH'S SPIN  ·  AT THE EQUATOR", 1670, lambda v: f"{fmt_int(v)} km/h", "× cos(latitude)  ·  London ≈ 1,040 km/h"),
    (LS["l08"] + 0.2, "EARTH AROUND THE SUN", 107000, lambda v: f"{fmt_int(v)} km/h", "≈ 29.8 km/s"),
    (LS["l12"] + 0.3, "THE SUN AROUND THE MILKY WAY", 828000, lambda v: f"≈ {fmt_int(v)} km/h", "≈ 230 km/s"),
    (LS["l16"] + 9.0, "THE SUN RELATIVE TO THE COSMIC MICROWAVE BACKGROUND", 1.33,
     lambda v: f"≈ {v:.2f} million km/h", "≈ 370 km/s"),
    (LS["l18"] + 4.0, "THE LOCAL GROUP RELATIVE TO THE CMB", 2.2, lambda v: f"≈ {v:.1f} million km/h", "≈ 600 km/s"),
]
STACK_OUT = SC["why"][0] + 1.0


def overlays(img, t):
    # ---- distance counter (top-left), from l03
    o = win(t, LS["l03"] + 2.2, LS["l23"] - 0.8, 1.2, 1.2)
    km = V_CMB * t
    if o > 0:
        put_text(img, "DISTANCE YOU'VE TRAVELLED SINCE THIS VIDEO STARTED", 70, 46, 15, (0.78, 0.78, 0.84), o,
                 "Inter-Regular.otf", 0.25)
        put_text(img, f"{fmt_int(km)} km", 68, 68, 52, (0.97, 0.96, 0.94), o, "Inter-ExtraLight.otf", 0.02)
        put_text(img, "at ≈ 370 km/s  ·  the Sun's speed relative to the cosmic microwave background", 70, 136, 14,
                 (0.66, 0.66, 0.72), o, "Inter-Regular.otf", 0.08)
    # ---- end: big counter (over the window side of the room), then the title
    o = win(t, LS["l23"] - 0.2, TOTAL, 1.4, 0)
    if o > 0:
        CX = 1310
        fo = 1 - smooth((t - (TOTAL - 0.5)) / 0.5)
        ob = o * fo
        m = ramp(t, LS["l25"] + 1.6, LS["l25"] + 4.0)
        yb = lerp(440, 560, m)
        sz = int(round(lerp(96, 64, m)))
        put_text(img, "SINCE THIS VIDEO STARTED", CX, yb - 48, 16, (0.8, 0.8, 0.86), ob, "Inter-Regular.otf", 0.3, "c")
        put_text(img, f"{fmt_int(km)} km", CX, yb, sz, (0.98, 0.97, 0.95), ob, "Inter-ExtraLight.otf", 0.02, "c")
        o2 = ob * win(t, LS["l23"] + 4.2, TOTAL, 1.0, 0)
        put_text(img, "ABOUT A QUARTER OF THE WAY TO THE MOON", CX, yb + sz + 30, 16, (0.78, 0.78, 0.84), o2,
                 "Inter-Regular.otf", 0.3, "c")
        ot = win(t, LS["l25"] + 2.0, TOTAL, 1.6, 0) * fo
        put_text(img, "YOU ARE NOT SITTING STILL", CX, 330, 46, (0.97, 0.96, 0.95), ot, "Inter-ExtraLight.otf", 0.30, "c")
    # ---- speed stack (bottom-left, grows upward)
    ot = 1 - smooth((t - STACK_OUT) / 1.5)
    vis = [s for s in STACK if t >= s[0] - 0.01]
    if ot > 0 and vis:
        y = H - 92
        dimk = 1.0
        for i, (t0, lab, val, fmtv, sub) in enumerate(vis):
            a = smooth((t - t0) / 0.8) * ot * dimk
            c = ease((t - t0) / 1.8)
            v = val * c
            newest = (i == len(vis) - 1) and (t - t0 < 6)
            col = (1.0, 0.93, 0.80) if newest else (0.94, 0.93, 0.92)
            put_text(img, lab, 70, y - 50, 13, (0.72, 0.72, 0.78), a, "Inter-Regular.otf", 0.25)
            w = put_text(img, fmtv(v), 68, y - 32, 30, col, a, "Inter-Light.otf", 0.02)
            put_text(img, sub, 70 + w + 14, y - 22, 14, (0.64, 0.64, 0.70), a, "Inter-Regular.otf", 0.06)
            y -= 76
    return img


# ================================================================== frame assembly with transitions
ORDER = TL["order"]
FN = dict(room=None, earth=scene_earth, orbit=scene_solar, helix=scene_solar, galaxy=scene_galaxy,
          cosmos=scene_cosmos, why=scene_why, end=scene_end)


def scene_room(t):
    z = lerp(1.18, 1.26, ramp(t, 0, SC["room"][1]))
    return room(t, z, 1150, 700)


FN["room"] = scene_room
XF = 1.0   # half-length of a crossfade (s)


def base_frame(t):
    # which scene(s)
    for i, sc in enumerate(ORDER):
        a, b = SC[sc]
        if a <= t < b or (i == len(ORDER) - 1):
            cur, nxt = sc, (ORDER[i + 1] if i + 1 < len(ORDER) else None)
            prv = ORDER[i - 1] if i > 0 else None
            break
    a, b = SC[cur]
    # orbit->helix is one continuous shot: no transition there
    def render(sc, tt):
        return FN[sc](tt)
    if nxt and t > b - XF and not (cur == "orbit" and nxt == "helix"):
        x = smooth((t - (b - XF)) / (2 * XF))
        A = zoom_img(render(cur, t), lerp(1.0, 0.82, x))
        B = zoom_img(render(nxt, t), lerp(1.3, 1.12, x))
        return A * (1 - x) + B * x
    if prv and t < a + XF and not (prv == "orbit" and cur == "helix"):
        x = smooth((t - (a - XF)) / (2 * XF))
        A = zoom_img(render(prv, t), lerp(1.0, 0.82, x))
        B = zoom_img(render(cur, t), lerp(1.3, 1.12, x) * 1 + 0 * ramp(t, a + XF, a + XF + 3))
        img = A * (1 - x) + B * x
        return img
    img = render(cur, t)
    # settle the incoming push (1.12 -> 1.0) over 3 s after a transition so it doesn't jump
    if prv and not (prv == "orbit" and cur == "helix") and t < a + XF + 3:
        img = zoom_img(img, lerp(1.12, 1.0, ramp(t, a + XF, a + XF + 3)))
    return img


def frame(fi):
    t = fi / FPS
    img = base_frame(t)
    if t < 0.8:
        img = img * smooth(t / 0.8)
    if t > TOTAL - 0.5:
        img = img * (1 - smooth((t - (TOTAL - 0.5)) / 0.5))
    img = overlays(img, t)
    return img


def main():
    a = sys.argv[1:]
    if "--stills" in a:
        os.makedirs(S + "/prev", exist_ok=True)
        for s in a[a.index("--stills") + 1].split(","):
            t0 = time.time()
            fi = int(round(float(s) * FPS))
            to8(frame(fi)).save(f"{S}/prev/still_{float(s):06.1f}.png")
            print(f"still {s}  {time.time() - t0:.2f}s", flush=True)
        return
    k = int(a[a.index("--part") + 1]); n = int(a[a.index("--parts") + 1])
    os.makedirs(S + "/parts", exist_ok=True)
    f0 = NF * k // n; f1 = NF * (k + 1) // n
    out = f"{S}/parts/part_{k:02d}.mp4"
    if os.path.exists(out):
        print("exists", out); return
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "fast", "-crf", "13",
                          "-pix_fmt", "yuv420p", "-threads", "1", out + ".tmp.mp4"], stdin=subprocess.PIPE)
    t0 = time.time()
    for fi in range(f0, f1):
        p.stdin.write((np.clip(frame(fi), 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
        if (fi - f0) % 48 == 0:
            print(f"part {k} frame {fi} ({fi - f0}/{f1 - f0}) {time.time() - t0:.0f}s", flush=True)
    p.stdin.close(); p.wait()
    os.rename(out + ".tmp.mp4", out)
    print("done", out, f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
