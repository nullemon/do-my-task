"""Shot list + renderer. Usage: python3 shots.py SHOT [SHOT ...]   (or 'list')
Each shot is rendered by the numpy compositor straight into an x264 segment (no PNG frames on disk)."""
import sys, os, math, time
import numpy as np
from PIL import Image, ImageDraw
from common import *
import tv, cosmos

SH = PLACE["shots"]


def F(t):
    return int(round(t * FPS))


# ------------------------------------------------------------------------------ captions (absolute s)
CAPS = [
    (LS(2) + 0.4, LE(2) + 0.4, "RECEIVER NOISE · TRANSMITTERS · THE SUN", None),
    (LS(3) + 0.3, LE(3) + 0.8, "≈ 1% OF THE SNOW", "AN OFTEN-QUOTED ESTIMATE · NEVER PRECISELY MEASURED"),
    (LS(5) + 1.0, LE(5), "≈ 13.8 BILLION YEARS AGO", "THE UNIVERSE: HOT, DENSE, OPAQUE"),
    (LS(6) + 0.3, LE(6) + 0.6, "≈ 380,000 YEARS AFTER THE BIG BANG", "≈ 3,000 K"),
    (LS(7) + 0.2, LE(7) + 0.8, "THE UNIVERSE BECOMES TRANSPARENT", None),
    (LS(8) + 1.0, LE(8) + 0.5, "≈ 3,000 K · LIKE A COOL STAR", None),
    (LS(11) + 0.4, LE(11) + 0.5, "2.725 K · FROM EVERY DIRECTION", None),
    (LS(12) + 0.3, LE(12) + 0.5, "≈ 400 CMB PHOTONS IN EVERY CUBIC CENTIMETRE", None),
    (LS(14) + 0.6, LE(14) + 0.6, "HOLMDEL HORN ANTENNA · BELL LABS, NEW JERSEY", "STYLISED RECONSTRUCTION"),
    (LS(15) + 0.3, LE(15) + 0.4, "BUILT FOR PROJECT ECHO · 1960", "BALLOON SATELLITES FOR EARLY RADIO RELAY"),
    (LS(17) + 0.3, LE(17) + 0.6, "“WHITE DIELECTRIC MATERIAL”", "ARNO PENZIAS, ON THE PIGEON DROPPINGS"),
    (LS(19) + 0.3, LE(19) + 0.9, "“BOYS, WE'VE BEEN SCOOPED.”", "ROBERT DICKE, AS RECALLED BY HIS COLLEAGUES"),
    (LS(20) + 0.2, LE(20) + 0.9, "NOBEL PRIZE IN PHYSICS · 1978", "ARNO PENZIAS & ROBERT WILSON"),
    (LS(21) + 0.4, LE(21) + 0.4, "COBE 1989 · WMAP 2001 · PLANCK 2009", "LAUNCH YEARS"),
    (LS(22) + 0.4, LE(22) + 0.4, "VARIATIONS ≈ 1 PART IN 100,000", "A FEW HUNDRED-THOUSANDTHS OF A DEGREE"),
    (LS(25) + 3.0, LS(25) + 8.2, "UNITED STATES · FULL-POWER ANALOG OFF", "12 JUNE 2009"),
    (LS(25) + 8.6, LE(25) + 0.6, "UNITED KINGDOM · SWITCHOVER COMPLETE", "24 OCTOBER 2012"),
]


def overlay_captions(disp, t):
    for a, b, m, s in CAPS:
        if a - 0.1 <= t <= b + 0.1:
            caption(disp, t, a, b, m, s)


# ------------------------------------------------------------------------------ room shots
_ROOMS = {}


def room(cam):
    if cam not in _ROOMS:
        _ROOMS[cam] = tv.Room(cam)
    return _ROOMS[cam]


def shot_R1(fi):                                    # wide room, slow push
    t = fi / FPS
    R = room("wide")
    p = ss(0, SH["push"], t)
    z = 1.0 + 0.10 * (t / 14.0)
    cx = lerp(R.pw * 0.5, R.scr_cx, 0.25 * t / 14)
    cy = lerp(R.ph * 0.5, R.scr_cy, 0.25 * t / 14)
    d = R.frame(fi, z, cx, cy)
    return d * ss(0.0, 0.6, t)


def shot_R2(fi):                                    # medium, slow push towards the screen
    t = fi / FPS
    R = room("medium")
    p = (t - 14.05) / (SH["push"] - 14.05)
    z = 1.0 + 0.18 * p
    cx = lerp(R.pw * 0.52, R.pw * 0.52, p); cy = R.ph * 0.47
    return R.frame(fi, z, cx, cy)


_PF = None


def shot_PF(fi):
    global _PF
    if _PF is None:
        _PF = cosmos.PushFog(SH["push"], SH["stretch"])
    return _PF.frame(fi)


def shot_S1(fi):
    return cosmos.stretch_frame(fi)


def shot_S2(fi):
    return cosmos.every_dir_frame(fi)


def shot_S3(fi):
    return cosmos.cube_frame(fi)


def shot_S4(fi):                                    # back in the room: the rabbit ears
    t = fi / FPS
    R = room("medium")
    p = ss(119.0, SH["horn"], t)
    z = 1.25 + 0.2 * p
    d = R.frame(fi, z, R.pw * 0.53, R.ph * lerp(0.40, 0.34, p))
    return d * ss(119.0, 119.8, t) * (1 - ss(SH["horn"] - 0.6, SH["horn"], t))


# ------------------------------------------------------------------------------ horn shots
_IMG = {}


def plate_img(name):
    if name not in _IMG:
        _IMG[name] = srgb_to_lin(np.asarray(Image.open(os.path.join(PL, name)).convert("RGB")))
    return _IMG[name]


def shot_H1(fi):
    t = fi / FPS
    t0, t1 = SH["horn"], 138.0
    P = plate_img("horn_wide.png")
    p = (t - t0) / (t1 - t0)
    hp, wp = P.shape[:2]
    lin = zoom_crop(P, 1.0 + 0.12 * p, wp * (0.5 + 0.02 * p), hp * 0.5)
    d = lin
    return d * ss(t0, t0 + 1.0, t)


def _orbit(k):
    p = os.path.join(SCR, "frames", "horn_orbit", f"f_{k:04d}.png")
    im = Image.open(p).convert("RGB")
    if im.size != (W, H):
        im = im.resize((W, H), Image.LANCZOS)
    return srgb_to_lin(np.asarray(im))


def shot_H2(fi):                                    # 3D orbit: 41 key frames over 10 s, cross-blended in-betweens
    k6 = fi - F(138.0)
    k, rem = divmod(k6, 6)
    a = _orbit(min(k, 40))
    if rem and k < 40:
        w = ss(0, 1, rem / 6)
        a = a * (1 - w) + _orbit(k + 1) * w
    return a


def shot_H3(fi):                                    # 'day or night, whichever way they pointed it'
    t = fi / FPS
    t0, t1 = 148.0, 155.2
    S = 2
    day = 0.5 + 0.5 * math.cos((t - t0) / 3.6 * 2 * math.pi)       # day <-> night
    img = Image.new("RGB", (W * S, H * S), (0, 0, 0))
    d = ImageDraw.Draw(img)
    hy = int(H * 0.70 * S); cx = W // 2 * S; R = int(520 * S)
    for yy in range(0, hy, 8):
        f = yy / hy
        c = (lerp(3, 40, day) * (0.4 + 0.6 * f), lerp(5, 70, day) * (0.4 + 0.6 * f), lerp(12, 110, day) * (0.5 + 0.5 * f))
        d.rectangle([0, yy, W * S, yy + 8], fill=tuple(int(v) for v in c))
    d.rectangle([0, hy, W * S, H * S], fill=(4, 5, 4))
    d.line([0, hy, W * S, hy], fill=(90, 95, 100), width=2)
    d.arc([cx - R, hy - R, cx + R, hy + R], 180, 360, fill=(80, 90, 110), width=2)
    # sun / moon travelling across the dome
    sa = math.pi * (1 - ((t - t0) / 7.2 * 1.0) % 1.0)
    sx, sy = cx + R * 0.92 * math.cos(sa), hy - R * 0.92 * math.sin(sa)
    rs = 22 * S
    d.ellipse([sx - rs, sy - rs, sx + rs, sy + rs], fill=(int(lerp(200, 255, day)), int(lerp(205, 220, day)), int(lerp(215, 150, day))))
    # antenna pointing: eased between target angles
    targets = [62, 128, 34, 150, 95, 48, 115]
    seg = (t - t0) / 1.05
    i = int(seg); fpart = ss(0.0, 0.7, seg - i)
    ang = math.radians(lerp(targets[i % 7], targets[(i + 1) % 7], fpart))
    ax, ay = cx, hy - 6 * S
    L = R * 0.95
    for spread, col in ((0.07, (150, 180, 220)), (0.0, (220, 230, 245))):
        for sgn in ((-1, 1) if spread else (0,)):
            a2 = ang + sgn * spread
            d.line([ax, ay, ax + L * math.cos(a2), ay - L * math.sin(a2)], fill=col, width=2 if spread else 3)
    # horn icon
    ux, uy = math.cos(ang), -math.sin(ang); px_, py_ = -uy, ux
    pts = [(ax - ux * 10 * S + px_ * 8 * S, ay - uy * 10 * S + py_ * 8 * S), (ax + ux * 60 * S + px_ * 30 * S, ay + uy * 60 * S + py_ * 30 * S),
           (ax + ux * 60 * S - px_ * 30 * S, ay + uy * 60 * S - py_ * 30 * S), (ax - ux * 10 * S - px_ * 8 * S, ay - uy * 10 * S - py_ * 8 * S)]
    d.polygon(pts, fill=(170, 172, 168))
    # noise meter (right): constant excess
    mx, my = int(W * 0.84 * S), int(H * 0.22 * S)
    mh = int(340 * S); bw = 26 * S
    d.rectangle([mx, my, mx + bw, my + mh], outline=(120, 125, 135), width=2)
    lvl = 0.62 + 0.015 * math.sin(fi * 1.7) + 0.01 * math.sin(fi * 0.53)
    d.rectangle([mx + 4, my + mh * (1 - lvl), mx + bw - 4, my + mh - 4], fill=(225, 210, 170))
    img = img.resize((W, H), Image.LANCZOS)
    disp = (np.asarray(img).astype(np.float32) / 255) ** 2.2
    draw_text(disp, "EXCESS NOISE", W * 0.84 + 13, H * 0.22 - 30, 16, 0.75, tracking=0.35)
    draw_text(disp, "≈ 3.5 K", W * 0.84 + 13, H * 0.22 + 340 + 34, 26, 0.9, font=FONT_XL, tracking=0.2)
    draw_text(disp, "AT 4,080 MHz", W * 0.84 + 13, H * 0.22 + 340 + 70, 15, 0.6, tracking=0.35)
    draw_text(disp, "DAY" if day > 0.5 else "NIGHT", W / 2, H * 0.70 + 50, 18, 0.7, tracking=0.5)
    op = ss(t0, t0 + 0.6, t) * (1 - ss(t1 - 0.5, t1, t))
    return disp * op


class Pigeons:
    """Two pigeon silhouettes leaving the throat of the horn."""
    def draw(self, disp, t, t0):
        S = 2
        img = Image.new("L", (W * S, H * S), 0)
        d = ImageDraw.Draw(img)
        for k, (x0, y0, vx, vy, ph, delay) in enumerate(((1010, 270, -280, -120, 0.0, 0.0), (1075, 300, -320, -70, 1.7, 0.45))):
            tt = t - t0 - delay
            if tt < 0:
                x, y, flap = x0, y0, 0.2
            else:
                x = x0 + vx * tt - 8 * tt * tt * 0; y = y0 + vy * tt - 30 * tt * tt * -1
                flap = math.sin(tt * 2 * math.pi * 4.5 + ph)
            s = 9.0 * S
            X, Y = x * S, y * S
            body = [(X - 2.2 * s, Y), (X - 0.5 * s, Y - 0.6 * s), (X + 1.6 * s, Y - 0.3 * s), (X + 2.4 * s, Y - 0.8 * s),
                    (X + 2.6 * s, Y - 0.2 * s), (X + 1.4 * s, Y + 0.5 * s), (X - 1.0 * s, Y + 0.5 * s), (X - 3.0 * s, Y + 0.9 * s)]
            d.polygon(body, fill=255)
            wy = -2.6 * s * flap
            d.polygon([(X - 0.6 * s, Y - 0.2 * s), (X + 0.9 * s, Y - 0.2 * s), (X + 0.2 * s - 1.5 * s, Y + wy - 0.4 * s), (X - 2.2 * s, Y + wy)], fill=255)
        a = np.asarray(img.resize((W, H), Image.LANCZOS), np.float32)[..., None] / 255
        return disp * (1 - a * 0.92)


_PIG = Pigeons()


def shot_H4(fi):
    t = fi / FPS
    t0, t1 = 155.2, 165.2
    P = plate_img("horn_throat.png")
    hp, wp = P.shape[:2]
    p = (t - t0) / (t1 - t0)
    lin = zoom_crop(P, 1.05 + 0.08 * p, wp * 0.5, hp * 0.5)
    lin = _PIG.draw(lin, t, LS(17) + 0.4)
    return lin * ss(t0, t0 + 0.6, t)


def shot_H5(fi):                                    # Holmdel <-> Princeton
    t = fi / FPS
    t0, t1 = 165.2, 175.4
    lin = np.zeros((H, W, 3), np.float32) + 0.0006
    acc = Acc()
    # faint graticule
    gp = ss(t0, t0 + 1.0, t)
    ys = np.arange(80, H - 80, 6, dtype=np.float32); xs = np.arange(80, W - 80, 6, dtype=np.float32)
    gxs = np.concatenate([np.full_like(ys, xx) for xx in range(160, W, 160)] + [xs for yy in range(140, H, 160)])
    gys = np.concatenate([ys for xx in range(160, W, 160)] + [np.full_like(xs, yy) for yy in range(140, H, 160)])
    acc.add(gxs, gys, 0.06 * gp, np.array([0.5, 0.6, 0.8], np.float32))
    A = (1260.0, 470.0); B = (660.0, 500.0)             # Holmdel (east) / Princeton (west), ~40 km
    for (x, y), d0 in ((A, t0 + 0.4), (B, t0 + 1.6)):
        o = ss(d0, d0 + 0.8, t)
        acc.add(np.array([x]), np.array([y]), np.array([9.0 * o]), np.array([1.0, 0.85, 0.6], np.float32))
    lp = ss(t0 + 2.0, t0 + 4.0, t)
    s = np.linspace(0, lp, 500, dtype=np.float32)
    lx = A[0] + (B[0] - A[0]) * s; ly = A[1] + (B[1] - A[1]) * s - 40 * np.sin(np.pi * s / max(lp, 1e-3) * lp)
    dash = ((s * 60).astype(np.int32) % 2 == 0).astype(np.float32)
    acc.add(lx, ly, 0.5 * dash * (lp > 0), np.array([0.8, 0.85, 1.0], np.float32))
    im = blur(acc.image(), 1.2, 2) * 2.0
    lin = bloom(lin + im, 0.6, 14)
    disp = tonemap(lin, 1.6)
    o1 = ss(t0 + 0.8, t0 + 1.6, t); o2 = ss(t0 + 2.0, t0 + 2.8, t); o3 = ss(t0 + 4.0, t0 + 5.0, t)
    draw_text(disp, "HOLMDEL", A[0], A[1] + 42, 24, o1, tracking=0.4)
    draw_text(disp, "PENZIAS & WILSON · BELL LABS", A[0], A[1] + 76, 15, o1 * 0.7, tracking=0.35)
    draw_text(disp, "PRINCETON", B[0], B[1] + 42, 24, o2, tracking=0.4)
    draw_text(disp, "DICKE · PEEBLES · ROLL · WILKINSON", B[0], B[1] + 76, 15, o2 * 0.7, tracking=0.35)
    draw_text(disp, "≈ 40 KM", (A[0] + B[0]) / 2, (A[1] + B[1]) / 2 - 80, 18, o3 * 0.8, tracking=0.4)
    draw_text(disp, "1965 · TWO LETTERS, PUBLISHED SIDE BY SIDE IN THE ASTROPHYSICAL JOURNAL", W / 2, H * 0.80, 16,
              ss(LE(18) - 1.0, LE(18), t) * 0.75, tracking=0.3)
    op = ss(t0, t0 + 0.6, t) * (1 - ss(t1 - 0.5, t1, t))
    return disp * op


def shot_H6(fi):
    t = fi / FPS
    t0, t1 = 175.4, SH["map"]
    P = plate_img("horn_low.png")
    hp, wp = P.shape[:2]
    p = (t - t0) / (t1 - t0)
    lin = zoom_crop(P, 1.14 - 0.12 * p, wp * (0.52 - 0.03 * p), hp * (0.55 - 0.05 * p))
    return lin * ss(t0, t0 + 0.6, t) * (1 - ss(t1 - 1.0, t1, t))


_SKY = None


def shot_M(fi):
    global _SKY
    if _SKY is None:
        _SKY = cosmos.Sky()
    return cosmos.cmb_frames(_SKY, fi)


# ------------------------------------------------------------------------------ return + switch-off + title
T_OFF = LE(26) + 3.2          # the click


def shot_G(fi):
    t = fi / FPS
    t0 = SH["return"]
    R = room("wide")
    if t < 263.2:
        p = ss(t0, T_OFF, t)
        z = lerp(1.22, 1.0, p)
        cx = lerp(R.scr_cx, R.pw * 0.5, p); cy = lerp(R.scr_cy, R.ph * 0.5, p)
        collapse = None; on = 1.0
        if t >= T_OFF:
            dt = t - T_OFF
            sy = max(0.004, 1 - dt / 0.13) if dt < 0.13 else 0.004
            sx = 1.0 if dt < 0.13 else max(0.012, 1 - (dt - 0.13) / 0.22)
            dot = 1.0 if dt < 0.35 else math.exp(-(dt - 0.35) / 1.5)
            collapse = (sy, sx, dot)
            on = 1.0 if dt < 0.13 else max(0.0, 1 - (dt - 0.13) / 0.2)
        d = R.frame(fi, z, cx, cy, on=on, collapse=collapse)
        fade = ss(t0, t0 + 0.8, t) * (1 - ss(261.8, 263.2, t))
        return d * fade
    # title card
    disp = np.zeros((H, W, 3), np.float32)
    op = ss(263.8, 265.0, t) * (1 - ss(268.4, 269.5, t))
    draw_text(disp, "THE BIG BANG IS ON YOUR TV", W / 2, H / 2, 54, op, font=FONT_XL, tracking=0.32)
    return disp


SHOTS = [
    ("R1", 0.0, 14.05, shot_R1),
    ("R2", 14.05, SH["push"], shot_R2),
    ("PF", SH["push"], SH["stretch"], shot_PF),
    ("S1", SH["stretch"], 100.0, shot_S1),
    ("S2", 100.0, 109.0, shot_S2),
    ("S3", 109.0, 119.0, shot_S3),
    ("S4", 119.0, SH["horn"], shot_S4),
    ("H1", SH["horn"], 138.0, shot_H1),
    ("H2", 138.0, 148.0, shot_H2),
    ("H3", 148.0, 155.2, shot_H3),
    ("H4", 155.2, 165.2, shot_H4),
    ("H5", 165.2, 175.4, shot_H5),
    ("H6", 175.4, SH["map"], shot_H6),
    ("M", SH["map"], SH["return"], shot_M),
    ("G", SH["return"], PLACE["dur"], shot_G),
]
DISPLAY = {"H1", "H2", "H4", "H6"}     # these return linear values from display-referred plates


def render(name, only=None):
    for nm, a, b, fn in SHOTS:
        if nm != name:
            continue
        f0, f1 = F(a), F(b)
        frames = range(f0, f1) if only is None else only
        w = None if only is not None else Writer(nm)
        t_start = time.time()
        for fi in frames:
            out = fn(fi)
            if nm in DISPLAY:
                disp = out
            else:
                disp = out
            disp = np.array(disp, np.float32)
            overlay_captions(disp, fi / FPS)
            img = to8(disp)
            if w:
                w.write(img)
            else:
                Image.fromarray(img).save(os.path.join(SCR, f"test_{nm}_{fi}.png"))
            if (fi - f0) % 48 == 0:
                print(nm, fi, f"{time.time() - t_start:.0f}s", flush=True)
        if w:
            n = w.close()
            print(nm, "done", n, "frames", f"{time.time() - t_start:.0f}s", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "list":
        for nm, a, b, fn in SHOTS:
            print(nm, a, b, F(b) - F(a))
    elif sys.argv[1] == "test":
        nm = sys.argv[2]
        render(nm, only=[F(float(x)) for x in sys.argv[3:]])
    else:
        for nm in sys.argv[1:]:
            render(nm)
