"""Early-universe shots: push into the static -> plasma fog -> recombination -> glow;
light stretching; 'every direction'; photons per cm^3; CMB sky (artist's impression)."""
import numpy as np, math, os
from common import *
import tv

GY, GX = np.mgrid[0:H, 0:W].astype(np.float32)
GY2, GX2 = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32)
_NZ = {}


def noise_tex(seed, beta=2.6):
    if seed not in _NZ:
        _NZ[seed] = periodic_noise(1024, beta, seed)
    return _NZ[seed]


def bb_color(T):
    """Approximate display colour of a blackbody (normalised), T in K (valid ~1000-12000)."""
    T = max(T, 600.0) / 100.0
    r = 1.0 if T <= 66 else min(1, max(0, 1.2929 * (T - 60) ** -0.1332))
    g = (0.3901 * math.log(T) - 0.6318) if T <= 66 else 1.1299 * (T - 60) ** -0.0755
    b = 1.0 if T >= 66 else (0 if T <= 19 else 0.5432 * math.log(T - 10) - 1.1963)
    c = np.clip(np.array([r, g, b], np.float32), 0, 1)
    return c ** 2.2


ORANGE = bb_color(3000)


def fog_field(t, scale=1.0, drift=(0.0, 0.0)):
    """Smooth glowing plasma texture (half res, upsampled), mean ~1."""
    n1 = noise_tex(1); n2 = noise_tex(2, 2.2)
    x = (GX2 - W / 4) / scale + W / 4; y = (GY2 - H / 4) / scale + H / 4
    a = bilinear_wrap(n1, x * 0.9 + 40 * t + drift[0], y * 0.9 + 13 * t + drift[1])
    b = bilinear_wrap(n2, x * 2.3 - 25 * t + 300, y * 2.3 + 31 * t + 100)
    f = np.clip(1 + 0.30 * a + 0.12 * b, 0.05, None)
    f = np.repeat(np.repeat(f, 2, 0), 2, 1)
    return box1(box1(f, 1, 0), 1, 1)


class _NullAcc:
    def add(self, *a, **k):
        pass


# ============================================================== PUSH + FOG (34.5 -> 78.35)
class PushFog:
    def __init__(self, t0, t1):
        self.t0, self.t1 = t0, t1
        self.room = tv.Room("medium")
        r = np.random.default_rng(5)
        self.r = r
        self.NP, self.NE, self.NG = 700, 800, 520     # protons, electrons, photons
        self.px = r.uniform(0, W, self.NP); self.py = r.uniform(0, H, self.NP)
        self.pz = r.uniform(0, 1, self.NP)
        pair = r.integers(0, self.NP, self.NE)
        self.pair = pair
        self.ex = r.uniform(0, W, self.NE); self.ey = r.uniform(0, H, self.NE)
        self.ez = r.uniform(0, 1, self.NE)
        self.cap_t = r.uniform(LS(7) - 0.3, LS(7) + 2.6, self.NE)      # recombination moment per electron
        self.gx = r.uniform(0, W, self.NG); self.gy = r.uniform(0, H, self.NG)
        ang = r.uniform(0, 2 * np.pi, self.NG)
        self.gvx, self.gvy = np.cos(ang), np.sin(ang)
        self.gz = r.uniform(0, 1, self.NG)
        self.cap_x0 = None

    # -- stage timings (absolute seconds)
    def frame(self, fi):
        t = fi / FPS
        T_FOG = 41.0        # static fully dissolved into plasma by here
        if t < 37.2:
            # room push towards the screen
            p = ss(34.5, 37.6, t) ** 1.6
            zf = 2160 / (self.room.scr_h * 1.04) * self.room.pw / 3840
            z = lerp(1.18, zf, p)
            cx = lerp(self.room.pw * 0.52, self.room.scr_cx, ss(34.5, 36.5, t))
            cy = lerp(self.room.ph * 0.47, self.room.scr_cy, ss(34.5, 36.5, t))
            disp = self.room.frame(fi, z, cx, cy)
            if t > 36.4:
                Z = lerp(0.98, 1.4, ss(36.4, 37.6, t))
                c = tonemap(bloom(tv.crt_closeup(fi, Z), 0.3, 20), 1.5)
                disp = lerp(disp, c, ss(36.4, 37.2, t))
            return disp
        # close-up of the glass, zooming into the phosphor structure, then dissolving into plasma
        Z = 1.4 * math.exp(1.25 * (t - 37.2)) if t < 39.6 else 1.4 * math.exp(1.25 * 2.4) * (1 + 0.5 * (t - 39.6))
        pdis = ss(38.6, T_FOG, t)           # dissolve progress
        lin_static = None
        if pdis < 1:
            tint = (1 - ss(38.0, 40.0, t)) * tv.PHOS + ss(38.0, 40.0, t) * ORANGE / ORANGE.max()
            lin_static = tv.crt_closeup(fi, min(Z, 40), tint=tint, struct=1 - ss(39.0, 40.6, t))
            lin_static = bloom(lin_static, 0.3, 20)
        lin = self.plasma(fi, t)
        if lin_static is not None:
            n = noise_tex(3)
            d = bilinear_wrap(n, GX * 0.5, GY * 0.5) * 0.18 + 0.5
            m = np.clip((pdis * 1.6 - d) * 2.5 + 0.3 * pdis, 0, 1)[..., None]
            lin = lin_static * (1 - m) + lin * m
        disp = tonemap(lin, 1.25)
        # hand over to the stretch shot: dissolve into its opening frame (same glow, same noise field)
        if t > 76.6:
            disp = lerp(disp, stretch_frame(fi), ss(76.6, 78.35, t))
        return disp

    def plasma(self, fi, t, draw=True):
        """draw=False only advances the particle simulation (same RNG use) - for resuming in chunks."""
        r = self.r
        rec = ss(LS(7) - 0.2, LS(7) + 3.4, t)           # recombination progress (fog clears)
        late = ss(LS(8) - 0.5, LS(8) + 6.0, t)           # 'glows everywhere' pull-back
        # ---- background fog: very bright & opaque before, translucent amber glow after
        scale = 1.0 + 0.6 * late
        if draw:
            f = fog_field(t, scale)
            bright = lerp(0.36, 0.13, rec)
            col = lerp(bb_color(3700), ORANGE, ss(LS(6), LS(6) + 6, t))
            col = col / col.max()
            lin = (f * bright)[..., None] * col
        # ---- particles
        acc = Acc() if draw else _NullAcc()
        dt = 1.0
        # protons: slow jitter
        self.px += r.normal(0, 0.6, self.NP); self.py += r.normal(0, 0.6, self.NP)
        self.px %= W; self.py %= H
        # electrons: fast thermal jitter until captured
        jit = 5.0
        self.ex += r.normal(0, jit, self.NE); self.ey += r.normal(0, jit, self.NE)
        self.ex %= W; self.ey %= H
        capt = np.clip((t - self.cap_t) / 0.9, 0, 1)
        capt = capt * capt * (3 - 2 * capt)
        tx, ty = self.px[self.pair], self.py[self.pair]
        dx = (tx - self.ex + W / 2) % W - W / 2; dy = (ty - self.ey + H / 2) % H - H / 2
        exd = self.ex + dx * capt; eyd = self.ey + dy * capt
        self.ex = np.where(capt >= 1, tx, self.ex); self.ey = np.where(capt >= 1, ty, self.ey)
        depth_vis = lambda z: np.exp(-z * lerp(3.2, 0.6, rec))
        pcol = np.array([1.0, 0.55, 0.30], np.float32)
        ecol = np.array([0.55, 0.75, 1.0], np.float32)
        acol = np.array([0.95, 0.80, 0.62], np.float32)
        free_p = 1 - np.bincount(self.pair, weights=(capt >= 1), minlength=self.NP).clip(0, 1)
        pw = depth_vis(self.pz) * lerp(0.9, 0.55, rec)
        acc.add(self.px, self.py, 3.0 * pw * (0.4 + 0.6 * free_p), pcol)
        ew = depth_vis(self.ez) * (1 - capt) * 2.2
        acc.add(exd, eyd, ew, ecol)
        # photons: random walk (scatter) before, straight lines after
        sp = lerp(22.0, 34.0, rec)
        scat = 0.30 * (1 - rec) ** 2
        flip = r.random(self.NG) < scat
        ang = r.uniform(0, 2 * np.pi, self.NG)
        self.gvx = np.where(flip, np.cos(ang), self.gvx); self.gvy = np.where(flip, np.sin(ang), self.gvy)
        x0, y0 = self.gx.copy(), self.gy.copy()
        self.gx = self.gx + self.gvx * sp; self.gy = self.gy + self.gvy * sp
        wrap = (self.gx < -20) | (self.gx > W + 20) | (self.gy < -20) | (self.gy > H + 20)
        self.gx = np.where(wrap, self.gx % W, self.gx); self.gy = np.where(wrap, self.gy % H, self.gy)
        x0 = np.where(wrap, self.gx, x0); y0 = np.where(wrap, self.gy, y0)
        trail = lerp(1.0, 2.2, rec)
        NS = 14 if rec < 0.3 else 60
        sx, sy = segments(self.gx - (self.gx - x0) * trail, self.gy - (self.gy - y0) * trail, self.gx, self.gy, NS)
        gw = depth_vis(self.gz)[:, None] * np.linspace(0.15, 1.0, NS)[None, :] * (14 / NS) ** 0.8 * lerp(1.6, 0.75, rec)
        acc.add(sx, sy, gw, np.array([1.0, 0.93, 0.78], np.float32))
        if not draw:
            return None
        im = acc.image()
        im = blur(im, 1.4, 2) * 2.2
        lin = lin * (1 - 0.0 * im) + im
        lin = bloom(lin, 0.35, 18)
        return lin


# ============================================================== STRETCH (78.35 -> 100)
def temp_at(t):
    ks = [(78.0, 3000), (LS(10) + 0.2, 3000), (LS(10) + 1.4, 1500), (LS(10) + 3.2, 720),
          (LS(10) + 6.5, 40), (LS(10) + 9.2, 2.725)]
    if t <= ks[0][0]:
        return 3000.0
    for (a, ta), (b, tb) in zip(ks, ks[1:]):
        if t <= b:
            p = ss(a, b, t) if False else (t - a) / (b - a)
            p = p * p * (3 - 2 * p)
            return math.exp(lerp(math.log(ta), math.log(tb), p))
    return 2.725


def visible_lum(T):
    """Relative visible brightness of the glow as it cools (falls off a cliff below ~800 K)."""
    return float(np.clip((T - 650) / 2350, 0, 1) ** 1.3)


def fmt_temp(T):
    if T >= 100:
        return f"{int(round(T / 10) * 10):,} K"
    if T >= 10:
        return f"{T:.0f} K"
    return f"{T:.1f} K" if T > 2.75 else "2.7 K"


def stretch_frame(fi):
    t = fi / FPS
    T = temp_at(t)
    a = 3000.0 / T                  # stretch factor
    va = a ** 0.33                  # compressed visual stretch
    vis = visible_lum(T)
    # background: the orange glow fades into darkness as it reddens and disappears
    f = fog_field(t, 1.0 + 0.4 * (va - 1))
    bgk = ss(78.35, 80.0, t)        # first second: still the plasma glow from the previous shot
    gc = bb_color(max(T, 1000)); gc = gc / gc.max()
    bg_glow = lerp(0.36, 0.10, ss(78.35, LS(9) + 3.5, t)) * vis
    lin = (f * bg_glow)[..., None] * gc
    lin = lin + np.array([0.0008, 0.001, 0.002], np.float32)
    # comoving grid of 'space' points, spacing grows with the stretch
    acc = Acc()
    sp = 120 * va
    nx = int(W / sp) + 3; ny = int(H / sp) + 3
    ii, jj = np.meshgrid(np.arange(-nx, nx + 1), np.arange(-ny, ny + 1))
    gxp = W / 2 + ii * sp; gyp = H / 2 + jj * sp
    gp_op = ss(LS(9) + 1.5, LS(9) + 4, t)
    acc.add(gxp, gyp, 0.5 * gp_op, np.array([0.55, 0.6, 0.75], np.float32))
    # the light wave travelling left -> right
    xs = np.linspace(-20, W + 20, 6000, dtype=np.float32)
    lam = 110 * va
    phase = 2 * np.pi * (xs - 260 * t) / lam
    amp = 70 * (1 + 0.15 * (va - 1) ** 0.5)
    ys = H * 0.46 + amp * np.sin(phase)
    wop = ss(LS(9) - 1.0, LS(9) + 1.5, t)
    if vis > 0.002:
        wc = bb_color(max(T, 900)); wc = wc / wc.max()
        acc.add(xs, ys, 1.6 * wop * vis ** 0.6, wc)
    # invisible part: a faint grey-blue dashed trace standing in for microwaves
    inv = (1 - min(1, vis * 6)) * wop
    if inv > 0.002:
        dash = ((xs / 14).astype(np.int32) % 2 == 0).astype(np.float32)
        acc.add(xs, ys, 0.75 * inv * dash, np.array([0.45, 0.6, 0.85], np.float32))
    im = blur(acc.image(), 1.0, 2) * 2.0
    lin = lin + im
    lin = bloom(lin, 0.5, 16)
    disp = tonemap(lin, 1.6)
    # spectrum strip (log wavelength 300 nm .. 3 mm) with the peak-wavelength marker
    hud = ss(LS(9) + 0.5, LS(9) + 2.5, t)
    if hud > 0:
        draw_spectrum(disp, T, hud)
        draw_text(disp, "TEMPERATURE OF THE GLOW", W * 0.5, H * 0.135, 20, hud * 0.7, tracking=0.4)
        draw_text(disp, fmt_temp(T), W * 0.5, H * 0.19, 46, hud, font=FONT_XL, tracking=0.12)
        draw_text(disp, f"STRETCHED  ×{a:,.0f}" if a >= 1.5 else "STRETCHED  ×1", W * 0.5, H * 0.245, 20,
                  hud * 0.7, tracking=0.4)
    return disp


SPEC_X0, SPEC_X1, SPEC_Y = 300, 1620, 900
LMIN, LMAX = math.log10(300e-9), math.log10(3e-3)


def lam_x(lam):
    return SPEC_X0 + (math.log10(lam) - LMIN) / (LMAX - LMIN) * (SPEC_X1 - SPEC_X0)


_SPEC = None


def draw_spectrum(disp, T, op):
    global _SPEC
    if _SPEC is None:
        xs = np.arange(SPEC_X0, SPEC_X1)
        lam = 10 ** (LMIN + (xs - SPEC_X0) / (SPEC_X1 - SPEC_X0) * (LMAX - LMIN)) * 1e9
        col = np.zeros((len(xs), 3), np.float32)
        for i, l in enumerate(lam):
            if 380 <= l <= 750:
                # crude wavelength -> RGB
                if l < 440: c = (-(l - 440) / 60, 0, 1)
                elif l < 490: c = (0, (l - 440) / 50, 1)
                elif l < 510: c = (0, 1, -(l - 510) / 20)
                elif l < 580: c = ((l - 510) / 70, 1, 0)
                elif l < 645: c = (1, -(l - 645) / 65, 0)
                else: c = (1, 0, 0)
                fade = 1.0 if 420 < l < 700 else 0.4
                col[i] = np.array(c) * fade
            else:
                col[i] = (0.16, 0.16, 0.18)
        _SPEC = col
    y0, y1 = SPEC_Y - 3, SPEC_Y + 3
    reg = disp[y0:y1, SPEC_X0:SPEC_X1]
    disp[y0:y1, SPEC_X0:SPEC_X1] = reg * (1 - op * 0.9) + _SPEC[None] * op * 0.9
    for lab, l0, l1 in (("VISIBLE", 380e-9, 750e-9), ("INFRARED", 750e-9, 1e-3), ("MICROWAVE", 1e-3, 3e-3)):
        draw_text(disp, lab, (lam_x(l0) + lam_x(l1)) / 2, SPEC_Y + 26, 16, op * 0.6, tracking=0.4)
    lp = 2.898e-3 / T
    x = lam_x(lp)
    disp[SPEC_Y - 22:SPEC_Y - 6, int(x) - 1:int(x) + 1] = disp[SPEC_Y - 22:SPEC_Y - 6, int(x) - 1:int(x) + 1] * (1 - op) + op * 0.95
    lab = f"PEAK {lp * 1e6:,.1f} µm" if lp < 1e-4 else f"PEAK {lp * 1e3:.2f} mm"
    if lp < 1e-6:
        lab = f"PEAK {lp * 1e9:,.0f} nm"
    draw_text(disp, lab, x, SPEC_Y - 38, 16, op * 0.8, tracking=0.3)


# ============================================================== EVERY DIRECTION (100 -> 109)
def every_dir_frame(fi):
    t = fi / FPS
    t0 = 100.0
    op = ss(t0, t0 + 1.0, t) * (1 - ss(108.4, 109.0, t))
    acc = Acc()
    cx, cy = W / 2, H / 2
    R = 470
    # faint shell (the 'surface of last scattering', drawn as a ring)
    th = np.linspace(0, 2 * np.pi, 5000, dtype=np.float32)
    nz = bilinear_wrap(noise_tex(7), np.cos(th) * 200 + 500, np.sin(th) * 200 + 500)
    acc.add(cx + R * np.cos(th), cy + R * np.sin(th) * 0.98, 0.9 + 0.3 * nz, np.array([0.45, 0.6, 0.9], np.float32))
    # wavelets travelling inwards from every direction
    r = np.random.default_rng(3)
    n = 60
    ang = r.uniform(0, 2 * np.pi, n); ph = r.uniform(0, 1, n)
    for k in range(n):
        prog = (t * 0.22 + ph[k]) % 1.0
        rr = R * (1 - prog) + 4
        a = ang[k] + np.linspace(-0.09, 0.09, 60, dtype=np.float32)
        w = np.sin(np.pi * prog) ** 1.5 * 0.45
        for dr in (0, 10):
            acc.add(cx + (rr + dr) * np.cos(a), cy + (rr + dr) * np.sin(a), w * (1 - dr / 20), np.array([0.5, 0.7, 1.0], np.float32))
    # the Earth: tiny blue dot
    acc.add(np.array([cx]), np.array([cy]), np.array([6.0]), np.array([0.4, 0.65, 1.0], np.float32))
    im = blur(acc.image(), 1.3, 2) * 1.8
    lin = bloom(im + 0.0004, 0.6, 18)
    disp = tonemap(lin, 1.6) * op
    draw_text(disp, "YOU ARE HERE", cx, cy + 34, 15, op * 0.6 * ss(101.5, 102.5, t), tracking=0.4)
    return disp


# ============================================================== PHOTONS PER CM^3 (109 -> 119)
def cube_frame(fi):
    t = fi / FPS
    op = ss(109.0, 110.0, t) * (1 - ss(118.4, 119.0, t))
    acc = Acc()
    a = 0.35 + 0.08 * (t - 109)
    ca, sa = math.cos(a), math.sin(a)
    tilt = 0.42; ct, st = math.cos(tilt), math.sin(tilt)
    S = 300.0

    def proj(p):
        x, y, z = p[..., 0], p[..., 1], p[..., 2]
        x, z = x * ca + z * sa, -x * sa + z * ca
        y, z = y * ct - z * st, y * st + z * ct
        f = 1500 / (1500 + z * S)
        return W / 2 + x * S * f, H * 0.47 + y * S * f
    # edges
    corners = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], np.float32)
    edges = [(i, j) for i in range(8) for j in range(i + 1, 8) if np.sum(np.abs(corners[i] - corners[j])) == 2]
    s = np.linspace(0, 1, 400, dtype=np.float32)[:, None]
    for i, j in edges:
        p = corners[i] + (corners[j] - corners[i]) * s
        X, Y = proj(p)
        acc.add(X, Y, 0.35, np.array([0.7, 0.75, 0.85], np.float32))
    # ~411 photons, jittering
    r = np.random.default_rng(11)
    P = r.uniform(-1, 1, (411, 3)).astype(np.float32)
    wob = 0.05 * np.stack([np.sin(t * 1.3 * (1 + k % 7) + k) for k in range(3)], 0)
    rr = np.random.default_rng(fi)
    P2 = P + rr.normal(0, 0.012, P.shape).astype(np.float32) + wob[None, :] * 0
    X, Y = proj(P2)
    acc.add(X, Y, 1.3, np.array([0.6, 0.78, 1.0], np.float32))
    im = blur(acc.image(), 1.1, 2) * 1.8
    lin = bloom(im + 0.0004, 0.5, 14)
    disp = tonemap(lin, 1.6) * op
    draw_text(disp, "1 cm", W / 2, H * 0.47 + 345, 18, op * 0.7, tracking=0.3)
    return disp


# ============================================================== CMB SKY (192.2 -> 228.7)
def make_cmb(path, W2=3072, H2=1536, nwaves=700, seed=8):
    """Isotropic random field on the sphere = sum of plane waves evaluated on unit vectors."""
    r = np.random.default_rng(seed)
    lat = (0.5 - (np.arange(H2) + 0.5) / H2) * np.pi
    lon = ((np.arange(W2) + 0.5) / W2 - 0.5) * 2 * np.pi
    k = np.concatenate([r.uniform(3, 20, nwaves // 5), r.uniform(20, 140, nwaves - nwaves // 5)])
    amp = np.where(k < 20, 0.8, 1.0) * (k / 60) ** -0.6 * np.exp(-(k / 160) ** 2)
    d = r.standard_normal((nwaves, 3)); d /= np.linalg.norm(d, axis=1, keepdims=True)
    ph = r.uniform(0, 2 * np.pi, nwaves)
    out = np.zeros((H2, W2), np.float32)
    cl, sl = np.cos(lat)[:, None], np.sin(lat)[:, None]
    co, so = np.cos(lon)[None, :], np.sin(lon)[None, :]
    nx = (cl * co).astype(np.float32); ny = (cl * so).astype(np.float32); nz = np.broadcast_to(sl, (H2, W2)).astype(np.float32)
    for i in range(nwaves):
        kd = (k[i] * d[i]).astype(np.float32)
        out += np.float32(amp[i]) * np.cos(nx * kd[0] + ny * kd[1] + nz * kd[2] + np.float32(ph[i]))
    out = (out - out.mean()) / out.std()
    np.save(path, out.astype(np.float16))
    return out


def planck_cmap(v):
    """v ~ N(0,1) -> Planck-like diverging colours (linear RGB)."""
    stops = np.array([-2.6, -1.6, -0.7, 0.0, 0.7, 1.6, 2.6], np.float32)
    cols = np.array([[0.00, 0.01, 0.20], [0.02, 0.18, 0.75], [0.30, 0.65, 0.95], [0.97, 0.93, 0.80],
                     [1.00, 0.62, 0.18], [0.85, 0.15, 0.04], [0.30, 0.02, 0.01]], np.float32)
    out = np.empty(v.shape + (3,), np.float32)
    for c in range(3):
        out[..., c] = np.interp(v, stops, cols[:, c])
    return out ** 2.2


class Sky:
    def __init__(self):
        p = os.path.join(TEX, "cmb_equirect.npy")
        self.m = np.load(p).astype(np.float32) if os.path.exists(p) else make_cmb(p)
        self.h, self.w = self.m.shape
        r = np.random.default_rng(21)
        # 'galaxies' later: sample points biased towards hot spots (illustration of growth of structure)
        n = 400000
        u = r.uniform(0, 1, n); v = r.uniform(0, 1, n)
        val = self.m[(v * (self.h - 1)).astype(int), (u * (self.w - 1)).astype(int)]
        keep = r.uniform(0, 1, n) < np.clip(val - 0.3, 0, None) ** 3 * 0.12
        self.gu, self.gv = u[keep], v[keep]
        self.gb = r.uniform(0.3, 1.0, keep.sum())

    def sample_dir(self, x, y, z):
        lat = np.arcsin(np.clip(z, -1, 1)); lon = np.arctan2(y, x)
        u = (lon / (2 * np.pi) + 0.5) * self.w - 0.5
        v = (0.5 - lat / np.pi) * self.h - 0.5
        return bilinear_wrap(self.m, u, np.clip(v, 0, self.h - 1.001))

    def globe(self, t, R=430, cx=W / 2, cy=H / 2):
        X = (GX - cx) / R; Y = (GY - cy) / R
        r2 = X * X + Y * Y
        ins = r2 < 1
        Z = np.sqrt(np.clip(1 - r2, 0, 1))
        rot = 0.12 * t
        # view vector -> world: rotate about vertical axis, slight tilt
        tilt = 0.35
        x1, y1, z1 = Z, X, -Y
        y2 = y1 * math.cos(tilt) - z1 * math.sin(tilt) * 0; z2 = z1
        xw = x1 * math.cos(rot) - y1 * math.sin(rot); yw = x1 * math.sin(rot) + y1 * math.cos(rot)
        xt = xw * math.cos(tilt) + z2 * math.sin(tilt); zt = -xw * math.sin(tilt) + z2 * math.cos(tilt)
        val = self.sample_dir(xt, yw, zt)
        col = planck_cmap(val)
        shade = (0.55 + 0.45 * Z)[..., None]
        edge = np.clip((1 - np.sqrt(r2)) * R / 1.5, 0, 1)[..., None]
        return col * shade * edge * ins[..., None]

    def mollweide(self, zoom=1.0, cx=0.0, cy=0.0, scale=830):
        """Mollweide projection; zoom about (cx, cy) in map units."""
        X = ((GX - W / 2) / scale) / zoom + cx
        Y = (-(GY - H / 2) / scale) / zoom + cy
        # inverse Mollweide (R=1): x in [-2√2, 2√2], y in [-√2, √2]
        s2 = math.sqrt(2)
        ins = (X * X / 8 + Y * Y / 2) < 1
        th = np.arcsin(np.clip(Y / s2, -1, 1))
        lat = np.arcsin(np.clip((2 * th + np.sin(2 * th)) / np.pi, -1, 1))
        lon = np.pi * X / (2 * s2 * np.maximum(np.cos(th), 1e-4))
        ins &= np.abs(lon) <= np.pi
        u = (lon / (2 * np.pi) + 0.5) * self.w - 0.5
        v = (0.5 - lat / np.pi) * self.h - 0.5
        val = bilinear_wrap(self.m, u, np.clip(v, 0, self.h - 1.001))
        edge = np.clip((1 - (X * X / 8 + Y * Y / 2)) * scale * zoom / 3, 0, 1)
        return val, ins, edge, (u, v)


def cmb_frames(sky, fi):
    t = fi / FPS
    t0, t1 = 192.2, 228.7
    op_in = ss(t0, t0 + 1.2, t)
    tm = LS(22) - 0.8                           # globe -> map morph
    m_p = ss(tm, tm + 2.5, t)
    lin = np.zeros((H, W, 3), np.float32) + 0.0004
    if m_p < 1:
        g = sky.globe(t - t0, R=lerp(430, 520, ss(t0, tm, t)))
        lin = lin + g * (1 - m_p) * 0.85
    if m_p > 0:
        zst = LS(23) + 1.0                       # zoom into the map
        z = math.exp(lerp(0, math.log(3.4), ss(zst, zst + 9.0, t)))
        val, ins, edge, (u, v) = sky.mollweide(zoom=z, cx=lerp(0, -0.55, ss(zst, zst + 9, t)),
                                              cy=lerp(0, 0.25, ss(zst, zst + 9, t)), scale=lerp(300, 318, m_p))
        col = planck_cmap(val) * (ins * edge)[..., None]
        fade_map = 1 - ss(LS(23) + 4.5, LS(24) - 0.5, t) * 0.995
        lin = lin + col * m_p * 0.85 * fade_map
        # structure growth: points condensing on the hot spots
        gp = ss(LS(23) + 4.0, LS(24) + 0.5, t)
        if gp > 0:
            s2 = math.sqrt(2)
            lon = (sky.gu - 0.5) * 2 * np.pi; lat = (0.5 - sky.gv) * np.pi
            # forward Mollweide (Newton)
            th = lat.copy()
            for _ in range(6):
                th = th - (2 * th + np.sin(2 * th) - np.pi * np.sin(lat)) / (2 + 2 * np.cos(2 * th) + 1e-6)
            mx = 2 * s2 / np.pi * lon * np.cos(th); my = s2 * np.sin(th)
            cxm = lerp(0, -0.55, ss(zst, zst + 9, t)); cym = lerp(0, 0.25, ss(zst, zst + 9, t))
            sc = 318 * z
            px = W / 2 + (mx - cxm) * sc; py = H / 2 - (my - cym) * sc
            acc = Acc()
            acc.add(px, py, sky.gb * gp * 2.2, np.array([1.0, 0.9, 0.75], np.float32))
            im = blur(acc.image(), 1.0, 2) * 2.0
            lin = lin + im
    lin = bloom(lin, 0.35, 16)
    disp = tonemap(lin, 1.7)
    fade_out = 1 - ss(t1 - 1.2, t1 - 0.1, t)
    disp = disp * op_in * fade_out
    tag = ss(t0 + 1.0, t0 + 2.5, t) * (1 - ss(LS(23) + 5.0, LS(23) + 6.5, t)) * fade_out
    draw_text(disp, "ARTIST'S IMPRESSION · NOT REAL SATELLITE DATA", W - 60, 60, 15, tag * 0.6, anchor="r", tracking=0.3)
    return disp
