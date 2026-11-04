"""Analog snow, the CRT room composite and the CRT close-up."""
import numpy as np, os, math
from common import *

TW, TH = 1280, 480          # static texture: continuous-ish horizontally, one row per scan line
PHOS = np.array([0.86, 0.92, 1.0], np.float32)     # cool phosphor white


def static_tex(fi, seed=0):
    """One frame of analog 'snow': band-limited horizontal noise, per-line jitter, slow rolling band."""
    r = np.random.default_rng(fi * 7919 + seed * 104729 + 17)
    n = r.standard_normal((TH, TW), dtype=np.float32)
    n = box1(n, 2, 1) * np.float32(math.sqrt(5))          # ~ 4 MHz-ish smear along the line
    n += 0.25 * r.standard_normal((TH, 1), dtype=np.float32)  # line-to-line level jitter
    s = np.clip(0.46 + 0.30 * n, 0, 1) ** 1.5
    t = fi / FPS
    yy = np.arange(TH, dtype=np.float32)[:, None] / TH
    roll = (t * 0.11) % 1.3 - 0.15
    s *= 1 - 0.16 * np.exp(-((yy - roll) / 0.07) ** 2)
    # occasional brighter streak lines (impulse noise)
    k = r.integers(0, 5)
    for _ in range(k):
        y = r.integers(0, TH); x = r.integers(0, TW - 200); L = r.integers(40, 260)
        s[y, x:x + L] = np.minimum(1.0, s[y, x:x + L] + 0.5)
    return s


class Room:
    def __init__(self, cam):
        self.cam = cam
        self.off = np.load(os.path.join(PL, f"room_{cam}_off.npy"))
        self.lit = np.load(os.path.join(PL, f"room_{cam}_lit.npy"))
        self.uv = np.load(os.path.join(PL, f"room_{cam}_uv.npy"))
        m = self.uv[..., 2].astype(np.float32)
        ys, xs = np.nonzero(m > 0.5)
        self.scr_cx, self.scr_cy = float(xs.mean()), float(ys.mean())
        self.scr_h = float(ys.max() - ys.min()); self.scr_w = float(xs.max() - xs.min())
        self.ph, self.pw = m.shape
        self.ch = [np.ascontiguousarray(pl[..., c], np.float32) for pl in (self.off, self.lit, self.uv) for c in range(3)]

    def frame(self, fi, z, cx, cy, on=1.0, collapse=None, exposure=2.7, moon=0.26, tex=None):
        """Composite one frame. collapse=(sy, sx, dot) for the switch-off; tex: static texture override."""
        cx, cy = clamp_center(self.off.shape, z, cx, cy)
        allc = zoom_crop_ch(self.ch, z, cx, cy)
        off, lit, uv = allc[..., 0:3], allc[..., 3:6], allc[..., 6:9]
        if tex is None:
            tex = static_tex(fi)
        level = on
        flick = float(tex.mean()) if (collapse is None) else 0.45 * on
        if collapse is not None:
            level = collapse[2]
        k = 3.1 * flick * level * (1 + 0.03 * math.sin(fi * 2.1))
        lin = off * moon + lit * k
        # screen: only inside its bounding box
        m_full = uv[..., 2]
        rows = np.nonzero(m_full.max(1) > 0.002)[0]; cols = np.nonzero(m_full.max(0) > 0.002)[0]
        if rows.size and cols.size:
            y0, y1, x0, x1 = rows[0], rows[-1] + 1, cols[0], cols[-1] + 1
            uvb = uv[y0:y1, x0:x1]
            m = np.clip(uvb[..., 2], 0, 1)
            safe = np.maximum(m, 1e-4)
            u = np.clip(uvb[..., 0] / safe, 0, 1); v = np.clip(uvb[..., 1] / safe, 0, 1)
            iy = np.minimum(((1 - v) * TH).astype(np.int32), TH - 1)
            ix = np.minimum((u * TW).astype(np.int32), TW - 1)
            s = tex[iy, ix]
            du, dv = 2 * u - 1, 2 * v - 1
            du2, dv2 = du * du, dv * dv
            e8 = (du2 * du2) ** 2 + (dv2 * dv2) ** 2
            corner = np.clip((1 - np.sqrt(np.sqrt(np.sqrt(e8)))) * 40, 0, 1)
            vig = 1 - 0.30 * (du2 * 0.6 + dv2 * 0.8)
            if collapse is not None:
                sy, sx, dot = collapse
                inside = np.exp(-(dv / max(sy, 0.018)) ** 2 * 2.5) if sy < 0.999 else 1.0
                insidex = np.exp(-(du / max(sx, 0.024)) ** 2 * 2.5) if sx < 0.999 else 1.0
                gain = min(1.0 / max(sy, 0.02), 8.0) * (min(1.0 / max(sx, 0.05), 6.0) if sx < 0.999 else 1.0)
                if sy < 0.999:
                    s = (0.55 + 0.45 * s) * inside * insidex * gain
            scr = (s * vig * corner * (1.55 * level))[..., None] * PHOS
            hl = 0.018 * np.exp(-(((du + 0.45) ** 2) / 0.08 + ((dv - 0.55) ** 2) / 0.05))
            mm = (m * corner)[..., None]
            ob = off[y0:y1, x0:x1] * moon
            lb = lin[y0:y1, x0:x1]
            lin[y0:y1, x0:x1] = lb * (1 - mm) + mm * (ob + scr + hl[..., None])
        lin = bloom(lin, strength=0.55, r=26)
        return tonemap(lin, exposure)


def crt_closeup(fi, Z, tex=None, tint=None, struct=1.0, exposure=2.0, curv=0.07, sm=None):
    """Full-frame CRT screen: barrel-curved 4:3 glass, scan lines and aperture grille revealed with zoom.
    Z=1: screen fills the frame height. Returns linear RGB (before tonemap)."""
    gy, gx = np.mgrid[0:H, 0:W].astype(np.float32)
    X = (gx + 0.5 - W / 2) / (H / 2) / Z
    Y = (gy + 0.5 - H / 2) / (H / 2) / Z
    r2 = X * X * 0.56 + Y * Y
    Xd = X * (1 + curv * r2); Yd = Y * (1 + curv * r2)
    u = Xd / (4 / 3) * 0.5 + 0.5
    v = Yd * 0.5 + 0.5
    du, dv = 2 * u - 1, 2 * v - 1
    edge = (np.abs(du) ** 8 + np.abs(dv) ** 8) ** (1 / 8)
    inside = np.clip((1 - edge) * 60 * Z ** 0.5, 0, 1)
    if tex is None:
        tex = static_tex(fi)
    line = np.clip(v, 0, 0.99999) * TH
    iy = line.astype(np.int32)
    fyl = line - iy
    xs = np.clip(u, 0, 0.99999) * (TW - 1)
    x0 = xs.astype(np.int32); fx = xs - x0
    s = tex[iy, x0] * (1 - fx) + tex[iy, np.minimum(x0 + 1, TW - 1)] * fx
    px_per_line = H * Z / TH
    a_scan = struct * np.clip((px_per_line - 1.6) / 3.0, 0, 0.75)
    scan = 1 - a_scan * (1 - np.exp(-((fyl - 0.5) / 0.30) ** 2))
    vig = 1 - 0.35 * (du * du * 0.5 + dv * dv * 0.7)
    lum = s * scan * vig * inside
    col = np.broadcast_to(PHOS if tint is None else np.asarray(tint, np.float32), (H, W, 3))
    lin = lum[..., None] * col * 1.5
    # aperture grille: vertical R,G,B stripes, ~ 640 triads across the picture
    triads = 640
    px_per_stripe = (W * Z * 0.75 / 2) / (triads * 3) * 2 / 1.0
    a_gr = struct * np.clip((px_per_stripe - 1.4) / 2.5, 0, 0.85)
    if a_gr > 0.01:
        ph = (np.clip(u, 0, 1) * triads * 3) % 3.0
        rgb = np.stack([np.exp(-((ph - c - 0.5 + 1.5) % 3 - 1.5) ** 2 / 0.18) for c in range(3)], -1)
        rgb = rgb / rgb.max() * 3.0 / 1.0
        lin = lin * ((1 - a_gr) + a_gr * rgb * 0.75)
    # glass reflection + dark bezel tint
    bez = (1 - inside)[..., None] * np.array([0.004, 0.004, 0.005], np.float32)
    hl = 0.02 * np.exp(-(((du + 0.5) ** 2) / 0.06 + ((dv + 0.6) ** 2) / 0.05)) * inside
    return lin + bez + hl[..., None]
