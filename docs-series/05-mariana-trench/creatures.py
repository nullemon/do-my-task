"""Stylised deep-sea creatures (original, simplified designs) drawn procedurally with PIL polygons.
Every creature is drawn into small supersampled local canvases (body alpha + glow alpha) and composited
into the linear-light frame by `comp()`. Shapes come from a spine curve + width profile (fish, eel, squid arms)."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from common import W, H, blur

SS = 3


class Canvas:
    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0 = int(math.floor(max(-4000, x0))), int(math.floor(max(-4000, y0)))
        self.x1, self.y1 = int(math.ceil(min(W + 4000, x1))), int(math.ceil(min(H + 4000, y1)))
        self.w, self.h = max(1, self.x1 - self.x0), max(1, self.y1 - self.y0)
        self.im = Image.new("L", (self.w * SS, self.h * SS), 0)
        self.d = ImageDraw.Draw(self.im)

    def _p(self, pts):
        pts = np.asarray(pts, np.float64)
        return [((x - self.x0) * SS, (y - self.y0) * SS) for x, y in pts]

    def poly(self, pts, v=255):
        if len(pts) >= 3:
            self.d.polygon(self._p(pts), fill=int(v))

    def ellipse(self, cx, cy, rx, ry, v=255):
        self.d.ellipse([(cx - rx - self.x0) * SS, (cy - ry - self.y0) * SS, (cx + rx - self.x0) * SS, (cy + ry - self.y0) * SS],
                       fill=int(v))

    def line(self, pts, width, v=255):
        self.d.line(self._p(pts), fill=int(v), width=max(1, int(round(width * SS))), joint="curve")

    def alpha(self):
        a = self.im.reduce(SS)
        return np.asarray(a, np.float32) / 255.0


def comp(frame, cv, alpha, rgb, op=1.0, add=False, halo=0.0, halo_r=10):
    """Composite a canvas alpha into the frame. rgb: (3,) or (h,w,3). add=True -> emissive (additive)."""
    x0, y0 = cv.x0, cv.y0
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + cv.w), min(H, y0 + cv.h)
    if xb <= xa or yb <= ya or op <= 0:
        return
    a = alpha[ya - y0:yb - y0, xa - x0:xb - x0][..., None] * op
    col = np.asarray(rgb, np.float32)
    if col.ndim == 3:
        col = col[ya - y0:yb - y0, xa - x0:xb - x0]
    reg = frame[ya:yb, xa:xb]
    if add:
        reg += a * col
        if halo > 0:
            pad = int(halo_r * 2.5)
            X0, Y0, X1, Y1 = max(0, xa - pad), max(0, ya - pad), min(W, xb + pad), min(H, yb + pad)
            big = np.zeros((Y1 - Y0, X1 - X0), np.float32)
            big[ya - Y0:yb - Y0, xa - X0:xb - X0] = a[..., 0]
            hb = blur(big, halo_r)
            c = col if col.ndim == 1 else col.reshape(-1, 3).mean(0)
            frame[Y0:Y1, X0:X1] += hb[..., None] * c * halo
    else:
        reg[:] = reg * (1 - a) + a * col


def outline(spine, widths):
    spine = np.asarray(spine, np.float64)
    d = np.gradient(spine, axis=0)
    d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-9
    n = np.stack([-d[:, 1], d[:, 0]], 1)
    wl = np.asarray(widths)
    if wl.ndim == 1:
        wl = np.stack([wl, wl], 1)
    left = spine + n * wl[:, :1]
    right = spine - n * wl[:, 1:]
    return np.concatenate([left, right[::-1]], 0), n


def rot(pts, ang, cx=0.0, cy=0.0):
    c, s = math.cos(ang), math.sin(ang)
    p = np.asarray(pts, np.float64) - (cx, cy)
    return np.stack([p[:, 0] * c - p[:, 1] * s, p[:, 0] * s + p[:, 1] * c], 1) + (cx, cy)


def bbox(pts, pad=6):
    p = np.asarray(pts)
    return p[:, 0].min() - pad, p[:, 1].min() - pad, p[:, 0].max() + pad, p[:, 1].max() + pad


# ------------------------------------------------------------------------------------------ lanternfish
def lanternfish(frame, t, cx, cy, L, facing=1, ang=0.0, body_col=(0.003, 0.006, 0.012), glow=1.0,
                rim=(0.0, 0.0, 0.0), seed=0):
    """Small myctophid: blunt head, big eye, forked tail; rows of ventral photophores glow blue."""
    n = 26
    s = np.linspace(0, 1, n)
    ph = t * 9.0 + seed
    yw = np.sin(s * 5.0 - ph) * (s ** 2) * 0.07 * L
    spine = np.stack([(0.5 - s) * L * facing, yw], 1)
    wid = L * (0.115 * np.sin(np.pi * np.clip(s, 0, 1) ** 0.75) + 0.02) * (1 - 0.65 * s ** 3)
    poly, nrm = outline(spine, wid)
    tail_base = spine[-1]
    tail = np.array([tail_base + (0, -0.02 * L), tail_base + (-0.20 * L * facing, -0.17 * L + yw[-1] * 0.5),
                     tail_base + (-0.12 * L * facing, 0), tail_base + (-0.20 * L * facing, 0.17 * L + yw[-1] * 0.5),
                     tail_base + (0, 0.02 * L)])
    dfin = np.array([spine[9] + (0, -wid[9] * 0.9), spine[12] + (0, -wid[12] - 0.07 * L), spine[15] + (0, -wid[15] * 0.9)])
    parts = [rot(p, ang) + (cx, cy) for p in (poly, tail, dfin)]
    x0, y0, x1, y1 = bbox(np.concatenate(parts), 8)
    if x1 < 0 or x0 > W or y1 < 0 or y0 > H:
        return
    cv = Canvas(x0, y0, x1, y1)
    for p in parts:
        cv.poly(p)
    a = cv.alpha()
    comp(frame, cv, a, body_col)
    if any(rim):
        # rim on the upper edge from the faint light above
        top = np.clip(a - np.roll(a, 2, axis=0), 0, 1)
        comp(frame, cv, top, rim, add=True)
    # photophores: ventral row + a few on the head
    gv = Canvas(x0, y0, x1, y1)
    eye = rot([[spine[3, 0], spine[3, 1] - wid[3] * 0.15]], ang)[0] + (cx, cy)
    gl = []
    for k in range(4, 21, 3):
        p = spine[k] + (0, wid[k] * 0.72)
        gl.append(p)
    for k in range(8, 19, 5):
        gl.append(spine[k] + (0, wid[k] * 0.3))
    gl.append(spine[2] + (0, wid[2] * 0.55))
    gl = rot(gl, ang) + (cx, cy)
    r = max(0.8, L * 0.013)
    for (x, y) in gl:
        gv.ellipse(x, y, r, r)
    ga = gv.alpha()
    comp(frame, gv, ga, (0.25, 0.55, 1.6), op=glow, add=True, halo=0.9, halo_r=max(3, L * 0.04))
    ev = Canvas(eye[0] - L * 0.06 - 2, eye[1] - L * 0.06 - 2, eye[0] + L * 0.06 + 2, eye[1] + L * 0.06 + 2)
    ev.ellipse(eye[0], eye[1], L * 0.045, L * 0.045)
    comp(frame, ev, ev.alpha(), (0.006, 0.010, 0.018), op=0.8, add=True)


# ------------------------------------------------------------------------------------------ giant squid
def giant_squid(frame, t, cx, cy, L, body_col=(0.006, 0.003, 0.004), rim=(0.004, 0.012, 0.03), op=1.0):
    """Architeuthis-like silhouette, swimming fins-first to the left: mantle with terminal fins, head and eye,
    eight arms and two long feeding tentacles trailing to the right, undulating."""
    cv = Canvas(cx - L * 0.45, cy - L * 0.35, cx + L * 1.45, cy + L * 0.35)
    # mantle (from fin tip at x=-0.4L to head at x=0.15L)
    n = 30; s = np.linspace(0, 1, n)
    sp = np.stack([cx + (-0.40 + 0.55 * s) * L, cy + np.sin(t * 0.6) * 0.01 * L + 0 * s], 1)
    wid = L * (0.012 + 0.07 * np.sin(np.pi * np.clip(s * 0.9 + 0.08, 0, 1) ** 1.3))
    m_poly, _ = outline(sp, wid)
    cv.poly(m_poly)
    fin_flap = math.sin(t * 1.4) * 0.03 * L
    fin = np.array([[cx - 0.42 * L, cy], [cx - 0.30 * L, cy - 0.075 * L - fin_flap], [cx - 0.20 * L, cy],
                    [cx - 0.30 * L, cy + 0.075 * L + fin_flap]])
    cv.poly(fin)
    head = (cx + 0.19 * L, cy)
    cv.ellipse(head[0], head[1], 0.06 * L, 0.055 * L)
    # arms
    for k in range(8):
        off = (k - 3.5) / 3.5
        s2 = np.linspace(0, 1, 26)
        length = L * (0.42 + 0.06 * math.cos(k))
        ph = t * 1.2 + k * 0.7
        x = head[0] + 0.04 * L + s2 * length
        y = head[1] + off * 0.03 * L + off * s2 * 0.05 * L + np.sin(s2 * 4 - ph) * s2 * 0.035 * L
        w = L * 0.016 * (1 - s2) + 0.6
        p, _ = outline(np.stack([x, y], 1), w)
        cv.poly(p)
    # two long tentacles with clubs
    for k, sgn in enumerate((-1, 1)):
        s2 = np.linspace(0, 1, 60)
        length = L * 1.25
        ph = t * 0.9 + k * 1.9
        x = head[0] + 0.05 * L + s2 * length
        y = head[1] + sgn * 0.012 * L + np.sin(s2 * 5.5 - ph) * s2 * 0.06 * L + sgn * s2 * 0.03 * L
        w = L * (0.006 + 0.012 * np.exp(-((s2 - 0.9) / 0.05) ** 2)) + 0.5
        p, _ = outline(np.stack([x, y], 1), w)
        cv.poly(p)
    a = cv.alpha()
    comp(frame, cv, a, body_col, op=op)
    top = np.clip(a - np.roll(a, 3, axis=0), 0, 1)
    comp(frame, cv, top, rim, op=op, add=True)
    # the eye: the largest of any animal, catches the faint light
    ev = Canvas(head[0] - 0.04 * L, head[1] - 0.04 * L, head[0] + 0.04 * L, head[1] + 0.04 * L)
    ev.ellipse(head[0] - 0.005 * L, head[1] - 0.01 * L, 0.022 * L, 0.022 * L)
    comp(frame, ev, ev.alpha(), (0.010, 0.016, 0.03), op=op, add=True)


# ------------------------------------------------------------------------------------------ Atolla jelly
def atolla(frame, t, cx, cy, R, op=1.0):
    """Crown jellyfish with a 'burglar alarm' display: a wave of blue light chasing around its bell margin."""
    bv = Canvas(cx - R * 1.3, cy - R * 1.3, cx + R * 1.3, cy + R * 1.3)
    # faint deep-red bell (nearly invisible in the dark: red is the colour of invisibility here)
    ang = np.linspace(0, 2 * np.pi, 80)
    bell = np.stack([cx + np.cos(ang) * R * 0.95, cy + np.sin(ang) * R * 0.38 - R * 0.05], 1)
    bv.poly(bell)
    comp(frame, bv, bv.alpha(), (0.004, 0.0004, 0.0004), op=op)
    gv = Canvas(cx - R * 1.3, cy - R * 1.3, cx + R * 1.3, cy + R * 1.3)
    nseg = 22
    head = (t * 1.1) % 1.0
    burst = 0.5 + 0.5 * math.sin(t * 0.9) ** 2
    for k in range(nseg):
        th = 2 * np.pi * k / nseg
        ph = (k / nseg - head) % 1.0
        v = math.exp(-ph * 5.0) * burst + 0.12
        x = cx + math.cos(th) * R; y = cy + math.sin(th) * R * 0.4
        gv.ellipse(x, y, R * 0.05 + 1, R * 0.03 + 1, v=255 * min(1, v))
        # short marginal tentacles
    for k in range(nseg * 2):
        th = 2 * np.pi * (k + 0.5) / (nseg * 2)
        x = cx + math.cos(th) * R * 1.02; y = cy + math.sin(th) * R * 0.41
        gv.line([(x, y), (x + math.cos(th) * R * 0.08, y + R * 0.25 + math.sin(t + k) * 4)], 0.6, v=40)
    comp(frame, gv, gv.alpha(), (0.18, 0.55, 1.9), op=op, add=True, halo=1.4, halo_r=max(6, R * 0.25))


# ------------------------------------------------------------------------------------------ anglerfish
def anglerfish(frame, t, cx, cy, L, op=1.0, lure_gain=1.0):
    """Female deep-sea anglerfish (ceratioid): globular dark body, huge jaw with needle teeth, the illicium
    (a modified dorsal fin spine) arching forward, tipped with a glowing esca. Facing left."""
    x0, y0, x1, y1 = cx - L * 0.95, cy - L * 0.75, cx + L * 0.8, cy + L * 0.6
    cv = Canvas(x0, y0, x1, y1)
    ang = np.linspace(0, 2 * np.pi, 90)
    rx, ry = L * 0.42, L * 0.33
    mouth_open = 0.30 + 0.05 * math.sin(t * 0.8)
    body = np.stack([cx + np.cos(ang) * rx, cy + np.sin(ang) * ry], 1)
    cv.poly(body)
    tail = np.array([[cx + rx * 0.9, cy - ry * 0.15], [cx + L * 0.7, cy - L * 0.18 + math.sin(t * 2) * 5],
                     [cx + L * 0.64, cy + math.sin(t * 2 + 1) * 3], [cx + L * 0.7, cy + L * 0.16 + math.sin(t * 2) * 5],
                     [cx + rx * 0.9, cy + ry * 0.2]])
    cv.poly(tail)
    for k in range(3):     # small pectoral / ventral fins
        bx = cx + rx * 0.2 + k * 6; by = cy + ry * 0.6
        cv.poly([(bx, by), (bx + L * 0.12, by + L * 0.1 + math.sin(t * 3 + k) * 3), (bx + L * 0.05, by + 2)])
    a = cv.alpha()
    # lighting: the body is only seen by the light of its own lure
    sw = math.sin(t * 0.7) * 0.03 * L
    esca = (cx - L * 0.70 + sw, cy - L * 0.42 + math.cos(t * 0.5) * 0.02 * L)
    yy, xx = np.mgrid[cv.y0:cv.y0 + cv.h, cv.x0:cv.x0 + cv.w].astype(np.float32)
    dd = np.sqrt((xx - esca[0]) ** 2 + (yy - esca[1]) ** 2) / L
    lit = (0.06 / (0.05 + dd ** 2)) * lure_gain
    col = np.stack([0.010 * lit, 0.028 * lit, 0.034 * lit], -1) + np.array([0.0015, 0.002, 0.003], np.float32)
    comp(frame, cv, a, col, op=op)
    # gaping mouth: dark wedge, upper jaw edge and lower jaw edge lined with needle teeth
    mv = Canvas(x0, y0, x1, y1)
    ju = (cx - rx * 1.02, cy - ry * (0.30 + mouth_open * 0.5)); jl = (cx - rx * 1.06, cy + ry * (0.45 + mouth_open * 0.4))
    hinge = (cx - rx * 0.05, cy + ry * 0.12)
    mv.poly([ju, hinge, jl, (cx - rx * 0.8, cy + ry * 0.1)])
    comp(frame, mv, mv.alpha(), (0.0, 0.0, 0.0), op=op)
    tv = Canvas(x0, y0, x1, y1)
    for k in range(6):
        u = (k + 0.6) / 6.5
        tx = ju[0] + (hinge[0] - ju[0]) * u * 0.8; ty = ju[1] + (hinge[1] - ju[1]) * u * 0.8
        ln = L * (0.07 - 0.04 * u)
        tv.line([(tx, ty), (tx - ln * 0.15, ty + ln)], 1.2)
        bx = jl[0] + (hinge[0] - jl[0]) * u * 0.8; by = jl[1] + (hinge[1] - jl[1]) * u * 0.8
        tv.line([(bx, by), (bx - ln * 0.2, by - ln * 1.1)], 1.2)
    comp(frame, tv, tv.alpha(), (0.10, 0.17, 0.17), op=op * lure_gain, add=True)
    # illicium: arching rod from the top of the head to the esca
    iv = Canvas(x0, y0, x1, y1)
    s = np.linspace(0, 1, 30)
    base = (cx - rx * 0.25, cy - ry * 0.95)
    px = base[0] + (esca[0] - base[0]) * s
    py = base[1] + (esca[1] - base[1]) * s - np.sin(np.pi * s) * L * 0.18
    iv.line(np.stack([px, py], 1), 1.4)
    comp(frame, iv, iv.alpha(), (0.03, 0.06, 0.07), op=op * lure_gain, add=True)
    gv = Canvas(esca[0] - 40, esca[1] - 40, esca[0] + 40, esca[1] + 40)
    pulse = 0.75 + 0.25 * math.sin(t * 2.3) * math.sin(t * 0.7 + 1)
    gv.ellipse(esca[0], esca[1], L * 0.025 + 1.5, L * 0.03 + 1.5)
    comp(frame, gv, gv.alpha(), (0.6, 2.4, 2.0), op=op * pulse * lure_gain, add=True, halo=3.0, halo_r=max(8, L * 0.05))


# ------------------------------------------------------------------------------------------ gulper eel
def gulper(frame, t, cx, cy, L, op=1.0, body_col=(0.010, 0.011, 0.014)):
    """Pelican eel: enormous, loosely hinged mouth and a long whip-like body ending in a glowing tail organ."""
    n = 90
    s = np.linspace(0, 1, n)
    ph = t * 2.2
    x = cx + (s - 0.18) * L
    y = cy + np.sin(s * 9 - ph) * (0.015 + 0.05 * s) * L + s * 0.08 * L
    spine = np.stack([x, y], 1)
    wid = L * (0.022 * np.exp(-((s - 0.04) / 0.06) ** 2) + 0.010 * (1 - s) ** 1.5) + 0.5
    poly, _ = outline(spine, wid)
    open_ = 0.6 + 0.4 * math.sin(t * 0.6) ** 2
    jaw_len = 0.17 * L
    hx, hy = spine[0]
    u = np.linspace(0, 1, 16)
    # upper jaw: thin sliver reaching forward; lower jaw: longer sliver hanging down-forward; membrane between
    ux = hx - u * jaw_len; uy = hy - np.sin(u * 1.4) * 0.03 * L * open_
    lx = hx - u * jaw_len * 1.02; ly = hy + u * 0.10 * L * open_ + np.sin(u * 3.0) * 0.01 * L
    top, _ = outline(np.stack([ux, uy], 1), L * 0.004 * (1.4 - u) + 0.6)
    bot, _ = outline(np.stack([lx, ly], 1), L * 0.004 * (1.4 - u) + 0.6)
    sag = np.sin(np.pi * u) * 0.035 * L * open_
    pouch = np.concatenate([np.stack([ux, uy], 1)[::-1] * 0 + np.stack([lx, ly + sag * 0], 1)[::-1],
                            np.stack([hx + 0.03 * L - u * 0.03 * L, hy + 0.012 * L + u * 0.0], 1)[:1],
                            ], 0)
    pouch = np.concatenate([np.stack([lx, ly], 1), np.stack([lx[::-1] * 0.5 + hx * 0.5, (ly[::-1] + sag[::-1] * 1.6) * 0.6 + hy * 0.4 + 0.03 * L], 1)], 0)
    mouth_in = np.concatenate([np.stack([ux, uy], 1), np.stack([lx[::-1], ly[::-1]], 1)], 0)
    x0, y0, x1, y1 = bbox(np.concatenate([poly, top, bot, pouch]), 10)
    mv = Canvas(x0, y0, x1, y1); mv.poly(mouth_in)
    comp(frame, mv, mv.alpha(), (0.0, 0.0, 0.0), op=op * 0.3)
    cv = Canvas(x0, y0, x1, y1)
    cv.poly(poly); cv.poly(top); cv.poly(bot)
    a = cv.alpha()
    comp(frame, cv, a, body_col, op=op)
    pv = Canvas(x0, y0, x1, y1); pv.poly(pouch)    # thin translucent mouth membrane
    comp(frame, pv, pv.alpha(), body_col, op=op * 0.55)
    edge = np.clip(a - np.roll(a, 2, axis=0), 0, 1)
    comp(frame, cv, edge, (0.010, 0.016, 0.022), op=op, add=True)
    # tail light organ: pinkish glow with occasional red flashes
    tx, ty = spine[-1]
    fl = 0.5 + 0.5 * max(0.0, math.sin(t * 3.1)) ** 8 + 0.3 * math.sin(t * 1.3) ** 2
    gv = Canvas(tx - 30, ty - 30, tx + 30, ty + 30)
    gv.ellipse(tx, ty, 3.0, 2.2)
    comp(frame, gv, gv.alpha(), (1.6, 0.35, 0.55), op=op * fl, add=True, halo=2.5, halo_r=9)


# ------------------------------------------------------------------------------------------ sperm whale
def whale_shape(cx, cy, L, t):
    s = np.linspace(0, 1, 80)
    yw = np.sin(s * 3.0 - t * 0.9) * s ** 3 * 0.025 * L
    spine = np.stack([cx + (0.5 - s) * L, cy + yw + s * 0.02 * L], 1)
    # box head: deep and blunt for the front third, then tapering body
    wid_top = L * np.where(s < 0.33, 0.095 * (1 - np.exp(-s / 0.015)), 0.095 * (1 - (s - 0.33) / 0.67) ** 1.25 + 0.006)
    wid_bot = L * np.where(s < 0.33, 0.085 * (1 - np.exp(-s / 0.03)) * (0.55 + 1.35 * s), 0.10 * (1 - (s - 0.33) / 0.67) ** 1.1 + 0.006)
    poly, _ = outline(spine, np.stack([wid_top, wid_bot], 1))
    tb = spine[-1]
    fl = 0.07 * L
    flukes = np.array([tb + (0.02 * L, -0.004 * L), tb + (-0.05 * L, -fl * 0.35 + yw[-1]), tb + (-0.075 * L, -fl * 0.2 + yw[-1]),
                       tb + (-0.04 * L, 0), tb + (-0.075 * L, fl * 0.2 + yw[-1]), tb + (-0.05 * L, fl * 0.35 + yw[-1]),
                       tb + (0.02 * L, 0.004 * L)])
    jaw = np.array([spine[6] + (0, wid_bot[6] * 0.9), spine[28] + (0, wid_bot[28] * 1.05), spine[30] + (0, wid_bot[30] * 0.9)])
    pect = np.array([spine[30] + (0, wid_bot[30] * 0.8), spine[38] + (0.01 * L, 0.10 * L), spine[34] + (0, wid_bot[34] * 0.8)])
    return poly, flukes, jaw, pect


def sperm_whale(frame, t, cx, cy, L, op=1.0, rng=None):
    """Huge, dark, mostly invisible: traced by plankton it disturbs (bioluminescent sparks along its edges)."""
    poly, flukes, jaw, pect = whale_shape(cx, cy, L, t)
    x0, y0, x1, y1 = bbox(np.concatenate([poly, flukes, pect]), 20)
    cv = Canvas(x0, y0, x1, y1)
    for p in (poly, flukes, pect):
        cv.poly(p)
    a = cv.alpha()
    comp(frame, cv, a, (0.0, 0.0, 0.0), op=op * 0.92)
    # sparks along the outline
    gv = Canvas(x0, y0, x1, y1)
    r = np.random.default_rng(int(t * 24) // 3)
    ol = np.concatenate([poly, flukes])
    seg = np.linalg.norm(np.diff(ol, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    k = 260
    u = (np.arange(k) / k * cum[-1] + (t * 0.08 * cum[-1])) % cum[-1]
    px = np.interp(u, cum, ol[:, 0]); py = np.interp(u, cum, ol[:, 1])
    rr = np.random.default_rng(3)
    jitter = rr.normal(0, 4, (k, 2))
    vis = 0.5 + 0.5 * np.sin(rr.uniform(0, 6.28, k) + t * rr.uniform(1, 5, k))
    for (x, y), (jx, jy), v in zip(np.stack([px, py], 1), jitter, vis):
        if v > 0.55:
            gv.ellipse(x + jx, y + jy, 1.1, 1.1, v=255 * (v - 0.5) * 2)
    comp(frame, gv, gv.alpha(), (0.2, 0.75, 1.4), op=op, add=True, halo=1.2, halo_r=4)


# ------------------------------------------------------------------------------------------ dumbo octopus
def dumbo(frame, t, cx, cy, S, light=1.0, op=1.0):
    """Grimpoteuthis-like: pale bell-shaped body, two ear-like fins flapping, webbed arms forming a skirt."""
    flap = math.sin(t * 2.4)
    bob = math.sin(t * 2.4 - 0.6) * S * 0.05
    cy = cy + bob
    cv = Canvas(cx - S * 1.4, cy - S * 1.3, cx + S * 1.4, cy + S * 1.4)
    ang = np.linspace(math.pi, 2 * math.pi, 40)
    dome = np.stack([cx + np.cos(ang) * S * 0.48, cy - 0.1 * S + np.sin(ang) * S * 0.62], 1)
    # skirt: webbed arms flaring below, edge scalloped
    k = np.linspace(0, 1, 60)
    spread = 0.9 + 0.15 * math.sin(t * 2.4 + 1.2)
    sk_x = cx + (k - 0.5) * 2 * S * 0.72 * spread
    sk_y = cy + S * (0.32 + 0.20 * (1 - (2 * k - 1) ** 2)) + np.abs(np.sin(k * np.pi * 4)) * S * 0.08
    skirt = np.concatenate([dome, np.stack([sk_x[::-1], sk_y[::-1]], 1)[::-1]], 0)
    body = np.concatenate([dome, [[cx + S * 0.48, cy - 0.05 * S], [cx + S * 0.55 * spread, cy + 0.25 * S]],
                           np.stack([sk_x[::-1], sk_y[::-1]], 1), [[cx - S * 0.55 * spread, cy + 0.25 * S], [cx - S * 0.48, cy - 0.05 * S]]], 0)
    cv.poly(body)
    for sgn in (-1, 1):
        bx, by = cx + sgn * S * 0.40, cy - S * 0.42
        fin = [(bx, by - S * 0.10), (bx + sgn * S * 0.42, by - S * 0.20 - flap * S * 0.22),
               (bx + sgn * S * 0.48, by - S * 0.02 - flap * S * 0.20), (bx + sgn * S * 0.05, by + S * 0.12)]
        cv.poly(fin)
    # arm tips peeking under the web
    for j in range(8):
        u = (j + 0.5) / 8
        x = cx + (u - 0.5) * 2 * S * 0.62 * spread
        y = cy + S * (0.36 + 0.18 * (1 - (2 * u - 1) ** 2))
        cv.line([(x, y), (x + (u - 0.5) * S * 0.25, y + S * 0.22 + math.sin(t * 2 + j) * S * 0.03)], S * 0.03)
    a = cv.alpha()
    yy, xx = np.mgrid[cv.y0:cv.y0 + cv.h, cv.x0:cv.x0 + cv.w].astype(np.float32)
    shade = np.clip(1.15 - (yy - (cy - S * 0.7)) / (S * 2.0), 0.35, 1.2)
    col = np.stack([0.075 * shade, 0.050 * shade, 0.052 * shade], -1) * light
    comp(frame, cv, a, col, op=op)
    edge = np.clip(a - np.roll(a, 3, axis=0), 0, 1)
    comp(frame, cv, edge, (0.05, 0.04, 0.045), op=op * light, add=True)
    for sgn in (-1, 1):
        ex, ey = cx + sgn * S * 0.17, cy - S * 0.15
        ev = Canvas(ex - 8, ey - 8, ex + 8, ey + 8); ev.ellipse(ex, ey, S * 0.045, S * 0.05)
        comp(frame, ev, ev.alpha(), (0.004, 0.003, 0.004), op=op)


# ------------------------------------------------------------------------------------------ snailfish
def snailfish(frame, t, cx, cy, L, facing=1, light=1.0, op=1.0, seed=0):
    """Hadal snailfish (Pseudoliparis-like): big soft head, tapering tadpole body with long continuous fins,
    pale, translucent pink-white, scaleless."""
    n = 50; s = np.linspace(0, 1, n)
    ph = t * 3.0 + seed
    yw = np.sin(s * 4.5 - ph) * s ** 1.6 * 0.06 * L
    spine = np.stack([cx + (0.5 - s) * L * facing, cy + yw], 1)
    wid = L * (0.13 * np.exp(-((s - 0.10) / 0.16) ** 2) + 0.05 * (1 - s) ** 1.3 + 0.004) * np.clip(np.sqrt(np.clip(s / 0.06, 0, 1)) * 0.6 + 0.4, 0, 1)
    poly, nrm = outline(spine, wid)
    finw = L * 0.045 * np.clip((s - 0.3) / 0.15, 0, 1) * (1 - s) ** 0.3
    fin_top, _ = outline(spine, np.stack([wid + finw, -wid * 0.9], 1))
    fin_bot, _ = outline(spine, np.stack([-wid * 0.9, wid + finw], 1))
    x0, y0, x1, y1 = bbox(np.concatenate([fin_top, fin_bot, poly]), 12 + L * 0.08)
    fv = Canvas(x0, y0, x1, y1); fv.poly(fin_top); fv.poly(fin_bot)
    comp(frame, fv, fv.alpha(), (0.11 * light, 0.07 * light, 0.075 * light), op=op * 0.35)
    cv = Canvas(x0, y0, x1, y1); cv.poly(poly)
    hc = spine[3]
    cv.ellipse(hc[0], hc[1], L * 0.09, L * 0.115)
    for sgn in (-1, 1):    # large pectoral fins
        b = spine[9]
        cv.poly([b + (0, sgn * wid[9] * 0.3), b + (-0.12 * L * facing, sgn * (wid[9] + 0.05 * L) + math.sin(t * 2) * 2),
                 b + (-0.18 * L * facing, sgn * wid[9] * 0.5)], v=150)
    a = cv.alpha()
    yy, xx = np.mgrid[cv.y0:cv.y0 + cv.h, cv.x0:cv.x0 + cv.w].astype(np.float32)
    shade = np.clip(1.25 - (yy - (cy - L * 0.2)) / (L * 0.55), 0.45, 1.25)
    col = np.stack([0.13 * shade, 0.085 * shade, 0.085 * shade], -1) * light
    comp(frame, cv, a, col, op=op * 0.85)
    # darker internal organs seen through the translucent body
    iv = Canvas(x0, y0, x1, y1)
    g = spine[14]
    iv.ellipse(g[0], g[1] + wid[14] * 0.2, L * 0.07, L * 0.045)
    comp(frame, iv, iv.alpha(), (0.05 * light, 0.025 * light, 0.03 * light), op=op * 0.5)
    e = spine[4] + (0, -wid[4] * 0.3)
    ev = Canvas(e[0] - 6, e[1] - 6, e[0] + 6, e[1] + 6); ev.ellipse(e[0], e[1], L * 0.018 + 0.6, L * 0.018 + 0.6)
    comp(frame, ev, ev.alpha(), (0.006, 0.004, 0.005), op=op)


# ------------------------------------------------------------------------------------------ amphipod
def amphipod(frame, t, cx, cy, L, ang=0.0, light=1.0, op=1.0, seed=0):
    """Hirondellea-like amphipod: curved, laterally flattened segmented body, pale amber-white, with legs."""
    nseg = 11
    s = np.linspace(0, 1, 40)
    curl = 1.25 + 0.15 * math.sin(t * 5 + seed)
    th = (s - 0.5) * curl
    R = L / curl
    sp = np.stack([np.sin(th) * R, -np.cos(th) * R + R], 1)
    wid = L * (0.13 * np.sin(np.pi * np.clip(s * 0.95 + 0.04, 0, 1)) ** 0.5 + 0.01)
    poly, nrm = outline(sp, np.stack([wid * 0.6, wid * 1.0], 1))
    parts = [rot(poly, ang) + (cx, cy)]
    legs = []
    for k in range(7):
        i = 8 + k * 3
        b = sp[i] + nrm[i] * (-wid[i])
        tip = b + nrm[i] * (-L * 0.22) + (math.sin(t * 9 + k + seed) * L * 0.05, 0)
        legs.append(rot([b, tip], ang) + (cx, cy))
    ant = [rot([sp[1], sp[1] + (-L * 0.35, -L * 0.18 + math.sin(t * 4 + seed) * L * 0.04)], ang) + (cx, cy),
           rot([sp[1], sp[1] + (-L * 0.30, -L * 0.05)], ang) + (cx, cy)]
    allp = np.concatenate(parts + legs + ant)
    x0, y0, x1, y1 = bbox(allp, 6)
    if x1 < 0 or x0 > W or y1 < 0 or y0 > H:
        return
    cv = Canvas(x0, y0, x1, y1)
    cv.poly(parts[0])
    for lg in legs + ant:
        cv.line(lg, max(0.5, L * 0.025))
    a = cv.alpha()
    comp(frame, cv, a, (0.22 * light, 0.17 * light, 0.11 * light), op=op)
    # segment lines
    sv = Canvas(x0, y0, x1, y1)
    for k in range(1, nseg):
        i = int(k / nseg * 39)
        p0 = sp[i] + nrm[i] * wid[i] * 0.6; p1 = sp[i] - nrm[i] * wid[i]
        sv.line(rot([p0, p1], ang) + (cx, cy), 0.6)
    comp(frame, sv, sv.alpha() * a, (0.08 * light, 0.06 * light, 0.04 * light), op=op * 0.7)
