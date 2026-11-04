"""
03 "You Are Not Sitting Still" - pre-baked 2D assets (numpy + PIL, run once, /usr/bin/python3).

  room_base.png   2400x1350  the dark room: wall, floor, window frame, chair, seated silhouette, side table + glass
  room_win.png    2400x1350  L mask: where the window glass is (the sky shows through)
  room_rim.png    2400x1350  soft starlight rim on the window-facing edges + light spill (added on top)
  sky_win.png     3000x3000  night sky seen through the window: gradient, stars, faint Milky Way (rotated about the pole)
  horizon.png     2400x1350  RGBA distant hills + a few far-away town lights at the bottom of the window
  stars_space.png 3200x1800  deep-space star field used behind the 3D scenes
  cmb_map.png     1400x700   RGBA Mollweide all-sky map of the CMB dipole (motion toward l=264, b=48)

The silhouette is a generic, stylised figure (no likeness).
"""
import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

S = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/03-you-are-not-sitting-still"
OUT = S + "/tex"
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(3)
W, H = 2400, 1350
SS = 2  # supersampling for the vector drawing


def save(a, name, mode="RGB"):
    a = np.clip(a, 0, 1)
    Image.fromarray((a * 255 + 0.5).astype(np.uint8), mode if a.ndim == 3 or mode == "L" else None).save(f"{OUT}/{name}")
    print("wrote", name, a.shape)


def gblur(a, r):
    im = Image.fromarray((np.clip(a, 0, 1) * 65535).astype(np.uint16)) if False else None
    # float gaussian blur via PIL on 8-bit would band; do separable numpy box x3 (approx gaussian)
    out = a.astype(np.float32)
    k = max(1, int(r))
    for _ in range(3):
        for ax in (0, 1):
            c = np.cumsum(np.pad(out, [(k + 1, k) if i == ax else (0, 0) for i in range(out.ndim)], mode="edge"), axis=ax)
            if ax == 0:
                out = (c[2 * k + 1:] - c[:-2 * k - 1]) / (2 * k + 1)
            else:
                out = (c[:, 2 * k + 1:] - c[:, :-2 * k - 1]) / (2 * k + 1)
    return out


def stars(w, h, n, seed, mag_slope=1.9, bright=1.0, col_var=True):
    r = np.random.default_rng(seed)
    img = np.zeros((h, w, 3), np.float32)
    ys = r.random(n) * h; xs = r.random(n) * w
    v = (r.pareto(mag_slope, n) + 1) ** 1.0 * 0.06 * bright
    v = np.minimum(v, 3.0)
    temp = r.random(n)
    cols = np.stack([np.interp(temp, [0, .3, .7, 1], [0.75, 0.95, 1.0, 1.0]),
                     np.interp(temp, [0, .3, .7, 1], [0.82, 0.95, 0.92, 0.80]),
                     np.interp(temp, [0, .3, .7, 1], [1.0, 1.0, 0.85, 0.62])], 1) if col_var else np.ones((n, 3))
    yi = ys.astype(int); xi = xs.astype(int); fy = ys - yi; fx = xs - xi
    for dy, wy in ((0, 1 - fy), (1, fy)):
        for dx, wx in ((0, 1 - fx), (1, fx)):
            yy = np.clip(yi + dy, 0, h - 1); xx = np.clip(xi + dx, 0, w - 1)
            for c in range(3):
                np.add.at(img[..., c], (yy, xx), v * wy * wx * cols[:, c])
    # bright stars get a small soft halo
    halo = gblur(img, 2) * 0.6
    return img + halo


# ------------------------------------------------------------------ sky through the window (rotates about the pole)
def sky():
    N = 3000
    y, x = np.mgrid[0:N, 0:N].astype(np.float32)
    img = stars(N, N, 26000, 11, bright=0.85)
    # faint Milky Way band (diagonal), mottled
    d = ((x - N / 2) * math.sin(0.9) - (y - N / 2) * math.cos(0.9) + 260) / N
    band = np.exp(-(d / 0.085) ** 2)
    noise = gblur(rng.random((N // 4, N // 4)).astype(np.float32), 3)
    noise = np.array(Image.fromarray((noise * 255).astype(np.uint8)).resize((N, N), Image.BICUBIC)).astype(np.float32) / 255
    band *= 0.4 + 1.2 * (noise - noise.min()) / (np.ptp(noise) + 1e-6)
    img += band[..., None] * np.array([0.050, 0.055, 0.075], np.float32)
    img += stars(N, N, 30000, 12, bright=0.25) * band[..., None] * 1.2
    save(img, "sky_win.png")


# ------------------------------------------------------------------ room
WX0, WY0, WX1, WY1 = 1280, 210, 2080, 1010       # window opening (final pixels)
FLOOR = 1150


def room():
    w, h = W * SS, H * SS
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    # wall: cold dark blue-grey, brighter around the window (starlight + skyglow), darker to the left & corners
    cx, cy = (WX0 + WX1) / 2, (WY0 + WY1) / 2
    dwin = np.sqrt(((x - cx) / 900) ** 2 + ((y - cy) / 700) ** 2)
    wall = 0.016 + 0.045 * np.exp(-dwin ** 2 * 0.9) + 0.030 * np.exp(-(((x - 900) / 520) ** 2 + ((y - 640) / 520) ** 2))
    base = np.stack([wall * 0.85, wall * 0.95, wall * 1.35], -1)
    # floor: slightly lighter, a soft light patch thrown by the window onto the floor (to the left: light comes in)
    fl = (y > FLOOR)
    fp = np.exp(-(((x - 1450) / 650) ** 2 + ((y - 1270) / 120) ** 2))
    floor = 0.012 + 0.05 * fp
    base = np.where(fl[..., None], np.stack([floor * 0.8, floor * 0.92, floor * 1.3], -1), base)
    # skirting line
    base[(y > FLOOR - 3) & (y < FLOOR + 2)] *= 0.4

    # vector layer (silhouette etc.) drawn at SS x
    sil = Image.new("L", (w, h), 0)
    win = Image.new("L", (w, h), 0)
    frm = Image.new("L", (w, h), 0)
    D = ImageDraw.Draw(sil); DW = ImageDraw.Draw(win); DF = ImageDraw.Draw(frm)
    s = SS
    P = lambda pts: [(px * s, py * s) for px, py in pts]
    # window glass + frame (frame drawn as dark mullions over the glass)
    DW.rectangle(P([(WX0, WY0), (WX1, WY1)]), fill=255)
    t = 22
    for (a, b, c, d) in [(WX0 - t, WY0 - t, WX1 + t, WY0), (WX0 - t, WY1, WX1 + t, WY1 + t + 6),
                         (WX0 - t, WY0 - t, WX0, WY1 + t), (WX1, WY0 - t, WX1 + t, WY1 + t),
                         ((WX0 + WX1) / 2 - 8, WY0, (WX0 + WX1) / 2 + 8, WY1),
                         (WX0, (WY0 + WY1) / 2 - 60, WX1, (WY0 + WY1) / 2 - 46)]:
        DF.rectangle(P([(a, b), (c, d)]), fill=255)
    # window sill
    DF.rectangle(P([(WX0 - 50, WY1 + t + 6), (WX1 + 50, WY1 + t + 22)]), fill=255)

    # --- chair (side view, facing right), simple modern wooden chair
    cxh = 930  # chair centre
    seat_y = 865
    D.rectangle(P([(cxh - 150, seat_y), (cxh + 120, seat_y + 22)]), fill=255)              # seat
    D.polygon(P([(cxh - 150, seat_y + 5), (cxh - 132, seat_y + 5), (cxh - 165, FLOOR), (cxh - 180, FLOOR)]), fill=255)  # back leg
    D.polygon(P([(cxh + 100, seat_y + 5), (cxh + 118, seat_y + 5), (cxh + 128, FLOOR), (cxh + 113, FLOOR)]), fill=255)  # front leg
    D.polygon(P([(cxh - 150, seat_y + 2), (cxh - 134, seat_y + 2), (cxh - 165, 560), (cxh - 182, 556)]), fill=255)     # backrest post
    D.rectangle(P([(cxh - 178, 600), (cxh - 150, 700)]), fill=255)                                                   # back slat
    D.line(P([(cxh - 160, seat_y + 150), (cxh + 112, seat_y + 150)]), fill=255, width=7 * s)                        # rung

    # --- seated figure in profile, facing the window (right). Smooth shapes.
    hx, hy = 930, 470            # head centre
    D.ellipse(P([(hx - 52, hy - 64), (hx + 50, hy + 60)]), fill=255)                         # skull
    D.polygon(P([(hx + 40, hy - 8), (hx + 58, hy + 18), (hx + 46, hy + 26), (hx + 44, hy + 46), (hx + 20, hy + 62)]), fill=255)  # nose/jaw
    D.polygon(P([(hx - 22, hy + 40), (hx + 20, hy + 44), (hx + 16, hy + 100), (hx - 30, hy + 96)]), fill=255)   # neck
    # torso: slightly reclined, shoulders back
    tor = []
    for k in range(41):
        u = k / 40.0
        # front contour (chest -> belly -> lap) and back contour (shoulder blade -> lower back)
        tor.append((hx + 30 + 28 * math.sin(math.pi * min(u * 1.2, 1)) - 10 * u, hy + 95 + u * (seat_y - 40 - hy - 95)))
    for k in range(41):
        u = 1 - k / 40.0
        tor.append((hx - 95 - 30 * math.sin(math.pi * u * 0.9) + 0 * u, hy + 110 + u * (seat_y + 10 - hy - 110)))
    D.polygon(P(tor), fill=255)
    D.polygon(P([(hx - 128, seat_y - 60), (hx + 40, seat_y - 75), (hx + 40, seat_y + 12), (hx - 128, seat_y + 12)]), fill=255)
    D.ellipse(P([(hx - 120, hy + 84), (hx + 50, hy + 200)]), fill=255)                     # shoulders
    # thigh (horizontal), knee, shin down to the floor, foot
    D.polygon(P([(hx - 120, seat_y - 70), (hx + 190, seat_y - 52), (hx + 205, seat_y + 8), (hx - 120, seat_y + 14)]), fill=255)
    D.ellipse(P([(hx + 160, seat_y - 60), (hx + 222, seat_y + 10)]), fill=255)             # knee
    D.polygon(P([(hx + 168, seat_y - 10), (hx + 220, seat_y - 14), (hx + 228, FLOOR - 40), (hx + 186, FLOOR - 36)]), fill=255)  # shin
    D.polygon(P([(hx + 180, FLOOR - 44), (hx + 232, FLOOR - 48), (hx + 300, FLOOR - 18), (hx + 302, FLOOR), (hx + 180, FLOOR)]), fill=255)  # shoe
    # arm: upper arm down from shoulder, forearm resting along the thigh, hand on the knee
    D.polygon(P([(hx - 40, hy + 110), (hx + 20, hy + 120), (hx + 30, seat_y - 120), (hx - 10, seat_y - 60), (hx - 50, seat_y - 80)]), fill=255)
    D.polygon(P([(hx - 20, seat_y - 112), (hx + 150, seat_y - 88), (hx + 156, seat_y - 52), (hx - 10, seat_y - 58)]), fill=255)
    # hair: slightly fuller back of head
    D.ellipse(P([(hx - 60, hy - 70), (hx + 36, hy + 20)]), fill=255)

    # --- small round side table by the window with a glass of water
    tx = 1330
    D.ellipse(P([(tx - 95, 840), (tx + 95, 862)]), fill=255)
    D.rectangle(P([(tx - 7, 850), (tx + 7, FLOOR - 10)]), fill=255)
    D.ellipse(P([(tx - 60, FLOOR - 16), (tx + 60, FLOOR + 4)]), fill=255)
    glass = Image.new("L", (w, h), 0); G = ImageDraw.Draw(glass)
    G.polygon(P([(tx - 22, 768), (tx + 22, 768), (tx + 18, 848), (tx - 18, 848)]), fill=255)

    def dn(im, blur=0):
        im = im.resize((W, H), Image.LANCZOS)
        if blur:
            im = im.filter(ImageFilter.GaussianBlur(blur))
        return np.asarray(im).astype(np.float32) / 255

    m_sil, m_win, m_frm, m_gl = dn(sil), dn(win), dn(frm), dn(glass)
    # glass is translucent: dark with a faint water line
    room = base.copy()
    winmask = np.clip(m_win - m_frm, 0, 1)
    room = room * (1 - winmask[..., None])
    frame_col = np.array([0.012, 0.013, 0.02], np.float32)
    room = room * (1 - m_frm[..., None]) + frame_col * m_frm[..., None]
    sil_col = np.array([0.004, 0.004, 0.007], np.float32)
    room = room * (1 - m_sil[..., None]) + sil_col * m_sil[..., None]
    # rim light: silhouette edge facing the window (+x) catches cold starlight
    shift = np.zeros_like(m_sil); k = 4
    shift[:, :-k] = m_sil[:, k:]
    rim = np.clip(m_sil - shift, 0, 1)
    rim = gblur(rim, 1) * (0.25 + 0.75 * np.clip((x - 700) / 700, 0, 1))
    rimc = rim[..., None] * np.array([0.16, 0.21, 0.32], np.float32)
    # the glass: faint highlight edges and a water surface line (perfectly flat -> "nothing moves")
    gl_edge = np.clip(m_gl - gblur(m_gl, 2), 0, 1) * 2.0
    water = ((y > 790) & (y < 793)).astype(np.float32) * m_gl
    room = room * (1 - 0.6 * m_gl[..., None]) + (gl_edge + 0.8 * water)[..., None] * np.array([0.10, 0.13, 0.19], np.float32)
    # light spill: subtle glow around the window into the room
    spill = gblur(winmask, 40) * 0.06
    rimc += spill[..., None] * np.array([0.5, 0.65, 1.0], np.float32) * (1 - winmask[..., None])
    save(room, "room_base.png")
    save(winmask, "room_win.png", "L")
    save(rimc, "room_rim.png")

    # horizon: dark hills + far town lights near the window bottom
    hz = np.zeros((H, W, 4), np.float32)
    xs = np.arange(W, dtype=np.float32)
    hill = WY1 - 70 - 40 * np.sin(xs / 210 + 1.3) - 22 * np.sin(xs / 77 + 0.4) - 10 * np.sin(xs / 31)
    hm = (y > hill[None, :]).astype(np.float32)
    hz[..., :3] = np.array([0.006, 0.007, 0.012])
    hz[..., 3] = hm
    # skyglow above the horizon (warm, faint)
    glow = np.exp(-np.clip(hill[None, :] - y, 0, None) / 60) * (1 - hm)
    hz[..., :3] += glow[..., None] * np.array([0.05, 0.035, 0.03])
    hz[..., 3] = np.maximum(hz[..., 3], glow * 0.9)
    n = 160
    lx = rng.uniform(WX0, WX1, n); ly = np.interp(lx, xs, hill) + rng.uniform(4, 40, n)
    for a, b in zip(lx, ly):
        r = rng.uniform(0.8, 1.8)
        yy, xx = np.mgrid[int(b) - 4:int(b) + 5, int(a) - 4:int(a) + 5]
        g = np.exp(-((xx - a) ** 2 + (yy - b) ** 2) / (r * r)) * rng.uniform(0.2, 0.7)
        hz[yy, xx, :3] += g[..., None] * np.array([1.0, 0.72, 0.42])
    save(hz, "horizon.png", "RGBA")


def space():
    img = stars(3200, 1800, 22000, 21, bright=0.9)
    img += stars(3200, 1800, 60000, 22, bright=0.18)
    save(img, "stars_space.png")


def cmb():
    w, h = 1400, 700
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    X = (x - w / 2) / (w / 2) * 2 * math.sqrt(2); Y = -(y - h / 2) / (h / 2) * math.sqrt(2)
    inside = (X / (2 * math.sqrt(2))) ** 2 + (Y / math.sqrt(2)) ** 2 <= 1
    th = np.arcsin(np.clip(Y / math.sqrt(2), -1, 1))
    lat = np.arcsin(np.clip((2 * th + np.sin(2 * th)) / math.pi, -1, 1))
    lon = -math.pi * X / (2 * math.sqrt(2) * np.cos(th) + 1e-9)       # galactic longitude, l=0 at centre, increasing to the left
    l0, b0 = math.radians(264.0), math.radians(48.3)
    v = np.stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)], -1)
    d = np.array([math.cos(b0) * math.cos(l0), math.cos(b0) * math.sin(l0), math.sin(b0)])
    dip = v @ d                                                      # +1 ahead (hotter), -1 behind (colder)
    # tiny primordial fluctuations (artistic hint, ~30x weaker than the dipole in reality is 100x)
    fl = gblur(rng.standard_normal((h, w)).astype(np.float32), 4); fl /= fl.std()
    t = np.clip(0.5 + 0.42 * dip + 0.035 * fl, 0, 1)
    cold = np.array([0.10, 0.30, 0.85]); mid = np.array([0.55, 0.50, 0.62]); hot = np.array([1.0, 0.55, 0.20])
    col = np.where(t[..., None] < 0.5, cold + (mid - cold) * (t[..., None] / 0.5), mid + (hot - mid) * ((t[..., None] - 0.5) / 0.5))
    edge = gblur(inside.astype(np.float32), 1)
    a = np.zeros((h, w, 4), np.float32)
    a[..., :3] = col * 0.85
    a[..., 3] = edge * 0.92
    # thin outline
    ol = np.clip(edge * (1 - edge) * 4, 0, 1)
    a[..., :3] += ol[..., None] * 0.5; a[..., 3] = np.maximum(a[..., 3], ol)
    # mark: direction of motion (small ring)
    X0 = None
    save(a, "cmb_map.png", "RGBA")
    # pixel of the motion direction for the compositor's marker
    th0 = b0
    for _ in range(30):
        th0 = th0 - (2 * th0 + math.sin(2 * th0) - math.pi * math.sin(b0)) / (2 + 2 * math.cos(2 * th0))
    lw = (l0 + math.pi) % (2 * math.pi) - math.pi
    px = w / 2 - (2 * math.sqrt(2) / math.pi * lw * math.cos(th0)) / (2 * math.sqrt(2)) * (w / 2)
    py = h / 2 - math.sqrt(2) * math.sin(th0) / math.sqrt(2) * (h / 2)
    open(f"{OUT}/cmb_apex.txt", "w").write(f"{px:.1f} {py:.1f}\n")
    print("apex px", px, py)


if __name__ == "__main__":
    import sys
    which = sys.argv[1:] or ["sky", "room", "space", "cmb"]
    for k in which:
        globals()[k]()
