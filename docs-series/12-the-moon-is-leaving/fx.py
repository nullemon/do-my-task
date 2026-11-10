"""Procedural renderers for "THE MOON IS LEAVING": Sun disc (granulation, spots, limb darkening), solar corona, the
eclipse geometry (rough lunar limb -> Baily's beads / diamond ring), molten proto-Earth + debris disc, a reflective sea,
rim-lit rock shores, Blender plate views. numpy + OpenCV, float32 display colour."""
from lib import *
from lib import _grid

_c = {}
def cached(key, fn):
    if key not in _c: _c[key] = fn()
    return _c[key]


def pnoise(w, h, octs=5, base=4, gain=0.55, seed=0, periodic_x=True, aspect=1.0):
    """fbm value noise (h,w) in -1..1; optionally periodic along x"""
    rng = np.random.default_rng(seed); out = np.zeros((h, w), F32); amp = 1.0; tot = 0; f = base
    for o in range(octs):
        nx = max(2, int(f)); ny = max(2, int(f * aspect * h / w) + 1)
        r = rng.uniform(-1, 1, (ny, nx)).astype(F32)
        if periodic_x: r = np.concatenate([r, r, r], 1)
        r = np.concatenate([r, r[:1]], 0) if False else r
        up = cv2.resize(r, (w * (3 if periodic_x else 1), h), interpolation=cv2.INTER_CUBIC)
        out += amp * (up[:, w:2 * w] if periodic_x else up); tot += amp; amp *= gain; f *= 2
    return out / tot


def tile_noise(n=1024, octs=6, base=4, gain=0.55, seed=0):
    """tileable fbm (n,n) via FFT-shaped spectrum"""
    rng = np.random.default_rng(seed); out = np.zeros((n, n), F32); amp = 1.0; tot = 0; f = base
    for o in range(octs):
        m = int(f); r = rng.uniform(-1, 1, (m, m)).astype(F32); r = np.tile(r, (3, 3))
        up = cv2.resize(r, (3 * n, 3 * n), interpolation=cv2.INTER_CUBIC)[n:2 * n, n:2 * n]
        out += amp * up; tot += amp; amp *= gain; f *= 2
    return out / tot


# ------------------------------------------------------------------------------------------------ Sun disc sprite
def sun_sprite(n=1500, kind="sun"):
    """RGBA-less float (n,n,3) + alpha: a filtered-light Sun (or a red giant) with granulation, spots, limb darkening"""
    def make():
        rng = np.random.default_rng(3 if kind == "sun" else 9)
        R = n * 0.47; c = n / 2
        y, x = np.mgrid[0:n, 0:n].astype(F32); u = (x - c) / R; v = (y - c) / R; rr = u * u + v * v
        mu = np.sqrt(np.clip(1 - rr, 0, 1))
        wn = rng.standard_normal((n, n)).astype(F32)
        if kind == "sun":
            g = cv2.GaussianBlur(wn, (0, 0), 1.6) - cv2.GaussianBlur(wn, (0, 0), 4.0); g /= g.std()
            sg = cv2.GaussianBlur(wn, (0, 0), 14) ; sg /= sg.std()
            tex_ = 1 + 0.085 * np.clip(g, -2.5, 2.5) * (0.35 + 0.65 * mu) + 0.03 * sg
            ld = 1 - 0.62 * (1 - mu) - 0.12 * (1 - mu) ** 2
            I = ld * tex_
            # sunspot groups (umbra + fibril penumbra) and faculae near the limb
            for (sx, sy, sr) in ((-0.32, 0.18, 0.030), (-0.26, 0.21, 0.016), (0.41, -0.22, 0.024), (0.47, -0.19, 0.012), (0.08, 0.36, 0.014), (-0.55, -0.30, 0.012)):
                d = np.hypot(u - sx, v - sy) / sr; ang = np.arctan2(v - sy, u - sx)
                fib = 0.75 + 0.25 * np.sin(ang * 26 + 3 * d)
                pen = np.clip((1.9 + 0.12 * np.sin(ang * 3 + sx * 40) + 0.06 * np.sin(ang * 7) - d) / 0.35, 0, 1); umb = np.clip((0.95 + 0.10 * np.sin(ang * 2 + 1) - d) / 0.3, 0, 1)
                I *= (1 - pen * (1 - 0.62 * fib)) * (1 - umb * 0.72)
            fac = np.clip(cv2.GaussianBlur(wn, (0, 0), 2.5) / 0.15 - 1.2, 0, 1) * np.clip(cv2.GaussianBlur(rng.standard_normal((n, n)).astype(F32), (0, 0), 40) * 40, 0, 1)
            I += 0.10 * fac * (1 - mu) ** 0.5
            col = np.stack([I * 1.0, I ** 1.18 * 0.74, I ** 1.9 * 0.30], -1) * 1.18
        else:
            q = n / 1500.0
            g = cv2.GaussianBlur(wn, (0, 0), 26 * q); g /= g.std(); g2 = cv2.GaussianBlur(wn, (0, 0), 9 * q); g2 /= g2.std(); g3 = cv2.GaussianBlur(wn, (0, 0), 3.5 * q); g3 /= g3.std()
            g4 = cv2.GaussianBlur(wn, (0, 0), 1.6 * q) - cv2.GaussianBlur(wn, (0, 0), 3.5 * q); g4 /= g4.std()
            lanes = np.clip(1 - np.abs(cv2.GaussianBlur(rng.standard_normal((n, n)).astype(F32), (0, 0), 12 * q)) * 12 * q * 6, 0, 1) ** 2
            cell = np.clip(0.5 + 0.26 * g + 0.20 * g2 + 0.13 * g3 + 0.07 * g4 - 0.22 * lanes, 0, 1.3)
            ld = 1 - 0.75 * (1 - mu) - 0.15 * (1 - mu) ** 2
            I = ld * (0.45 + 0.75 * cell)
            col = np.stack([I * 1.0, I ** 1.8 * 0.36, I ** 2.8 * 0.08], -1) * 0.95
        a = np.clip((1 - np.sqrt(rr)) * R + 0.5, 0, 1)
        return (col * a[..., None]).astype(F32), a.astype(F32), R
    return cached(("sunspr", n, kind), make)


def put_disc(img, spr, cx, cy, R, gain=1.0):
    col, a, R0 = spr; s = R / R0; n = col.shape[0]
    M = np.array([[s, 0, cx - s * n / 2], [0, s, cy - s * n / 2]], F32)
    inter = cv2.INTER_AREA if s < 0.7 else cv2.INTER_LINEAR
    if s < 0.5:
        k = int(1 / s); col = cv2.resize(col, (n // k, n // k), interpolation=cv2.INTER_AREA); a = cv2.resize(a, (n // k, n // k), interpolation=cv2.INTER_AREA)
        M = np.array([[s * k, 0, cx - s * n / 2], [0, s * k, cy - s * n / 2]], F32)
    c = cv2.warpAffine(col, M, (W, H), flags=cv2.INTER_LINEAR); al = cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_LINEAR)
    img *= (1 - al[..., None]); img += c * gain
    return al


# ------------------------------------------------------------------------------------------------ corona + eclipse
def corona_img(Rs, cx, cy, seed=2, rot=0.35):
    def make():
        y, x = np.mgrid[0:H, 0:W].astype(F32); dx = x - cx; dy = cy - y
        r = np.sqrt(dx * dx + dy * dy) / Rs; th = np.arctan2(dy, dx) - rot
        xx = np.maximum(r, 0.98); lx = np.log(xx)
        K = 1.5 * xx ** -8.0 + 0.55 * xx ** -3.4 + 0.07 * xx ** -1.9
        # streamers: (angle, width, strength); solar-minimum-like belt plus two mid-latitude helmets
        A = np.full_like(r, 0.20); S = np.zeros_like(r)
        for (t0, w0, st) in ((0.05, 0.42, 1.0), (math.pi + 0.10, 0.36, 0.95), (0.95, 0.20, 0.55), (-0.75, 0.17, 0.45), (math.pi - 0.8, 0.22, 0.5), (math.pi + 0.95, 0.16, 0.4)):
            d = np.angle(np.exp(1j * (th - t0))).astype(F32); w = w0 / (1 + 0.55 * lx * 2.2)
            gs = np.exp(-(d / w) ** 2); A += st * gs; S += st * gs * 0.22 * xx ** -1.25
        # field-line following coordinates: rays fan away from the poles (dipole-like)
        ths = th + 0.42 * np.sin(2 * th) * np.clip(lx, 0, 2.0) * 0.6
        N1 = pnoise(2048, 256, 5, 48, 0.6, seed, aspect=0.25); N2 = pnoise(2048, 256, 4, 300, 0.6, seed + 1, aspect=0.06)
        mx = ((ths / (2 * np.pi)) % 1.0 * 2048).astype(F32); my = np.clip(lx / 1.9 * 255, 0, 255).astype(F32)
        n1 = cv2.remap(N1, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP); n2 = cv2.remap(N2, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        pol = np.abs(np.sin(th)) ** 3                                   # polar plumes are finer and crisper
        stri = np.clip(0.66 + 1.0 * n1 + (0.35 + 0.7 * pol) * n2, 0.10, 2.4)
        I = (K * A + S) * stri
        I = np.where(r >= 0.985, I, 0)
        I = 1 - np.exp(-I * 1.9)
        col = I[..., None] * np.array([0.93, 0.96, 1.0], F32)
        # chromosphere + prominences (pink)
        pk = np.exp(-((r - 1.004) / 0.006) ** 2) * 0.9
        for (t0, wd, hh, amp) in ((0.9, 0.035, 0.035, 1.0), (2.6, 0.02, 0.022, 0.8), (-1.9, 0.05, 0.028, 0.9), (-0.4, 0.015, 0.05, 0.7), (3.9, 0.025, 0.018, 0.6)):
            d = np.angle(np.exp(1j * (th - t0))).astype(F32)
            loop = np.exp(-((np.abs(d) / wd - 0.8 * np.clip((r - 1) / hh, 0, 1.5) * (1 - np.clip((r - 1) / hh, 0, 1))) / 0.55) ** 2)
            pk += amp * loop * np.exp(-np.clip(r - 1, 0, 9) / hh) * (r > 0.99) * (0.7 + 0.5 * n2)
        col += np.clip(pk, 0, 1.4)[..., None] * np.array([1.0, 0.22, 0.38], F32)
        return col.astype(F32)
    return cached(("corona", round(Rs, 1), round(cx), round(cy), seed), make)


_LIMB = None
def limb_profile(th):
    """relative lunar limb height vs position angle (exaggerated ~3x: real relief is up to ~0.2 % of the radius)"""
    global _LIMB
    if _LIMB is None:
        p = pnoise(1440, 2, 6, 20, 0.62, 77)[0]; q = pnoise(1440, 2, 4, 90, 0.6, 78)[0]
        _LIMB = (0.0052 * p + 0.0022 * q).astype(F32)
        k = np.arange(1440); _LIMB = np.clip(_LIMB, -0.0055, 0.01) - 0.0125 * np.exp(-((k - 832) / 5.0) ** 2).astype(F32)      # one deep valley: the last bead (the diamond)
    i = ((th / (2 * np.pi)) % 1.0) * 1440
    i0 = np.floor(i).astype(int) % 1440; f = (i - np.floor(i)).astype(F32)
    return _LIMB[i0] * (1 - f) + _LIMB[(i0 + 1) % 1440] * f


def eclipse(cx, cy, Rs, ratio, off, sky_day=(0.16, 0.25, 0.42), sky_dark=(0.012, 0.018, 0.040), corona=True, cor_gain=1.0, moon_M=None, spikes=1.0, stars=None, glare=1.0):
    """White-light view centred on the Sun. ratio = Moon/Sun apparent radius, off = Moon centre offset (px, x right y down).
    Returns (img, exposed fraction of the photosphere)."""
    SS = 2
    y, x = np.mgrid[0:H * SS, 0:W * SS].astype(F32); x = (x + 0.5) / SS; y = (y + 0.5) / SS
    rs = np.hypot(x - cx, y - cy)
    mxx = x - (cx + off[0]); myy = y - (cy + off[1]); rm = np.hypot(mxx, myy); thm = np.arctan2(-myy, mxx)
    Rm = Rs * ratio * (1 + limb_profile(thm))
    sunm = np.clip((Rs - rs) * SS * 0.5 + 0.5, 0, 1); moonm = np.clip((Rm - rm) * SS * 0.5 + 0.5, 0, 1)
    mu = np.sqrt(np.clip(1 - (rs / Rs) ** 2, 0, 1)); ld = 0.42 + 0.58 * mu
    P = cv2.resize(sunm * (1 - moonm) * ld, (W, H), interpolation=cv2.INTER_AREA)
    moon = cv2.resize(moonm, (W, H), interpolation=cv2.INTER_AREA)
    F = float(P.sum() / (math.pi * Rs * Rs * 0.8))
    dark = 1 - ss(0.0, 0.10, F) * 0.0 - min(1.0, F / 0.02) ** 0.5 if False else 1 - ss(0.0005, 0.06, F)
    sky = lerp(np.array(sky_day, F32), np.array(sky_dark, F32), 0.25 + 0.75 * dark)
    img = np.empty((H, W, 3), F32); img[:] = sky
    if stars is not None: img += stars * dark
    if corona:
        cg = cor_gain * (1 - 0.8 * ss(0.000002, 0.0012, F)) * (1 - ss(0.001, 0.01, F))
        if cg > 0.002:
            cor = corona_img(Rs, cx, cy)
            img += cor * cg
        # the inner corona / chromosphere survives a little longer than the outer streamers
    img *= (1 - moon[..., None])
    if moon_M is not None and dark > 0.5:
        es = np.zeros((H, W, 3), F32); draw_moon(es, cx + off[0], cy + off[1], Rs * ratio, moon_M, (0, 0, 1), exposure=0.0, earthshine=0.035 * (dark - 0.5) * 2, detail=0.5)
        img += es
    if F > 1e-7:
        small = cv2.resize(P, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
        g1 = cv2.GaussianBlur(small, (0, 0), 2.2); g2 = cv2.GaussianBlur(small, (0, 0), 9); g3 = cv2.resize(cv2.GaussianBlur(cv2.resize(small, (W // 8, H // 8), interpolation=cv2.INTER_AREA), (0, 0), 14), (W // 2, H // 2))
        g4 = cv2.resize(cv2.GaussianBlur(cv2.resize(small, (W // 16, H // 16), interpolation=cv2.INTER_AREA), (0, 0), 26), (W // 2, H // 2))
        gl = g1 * 2.2 + g2 * 2.6 + g3 * 5.0 + g4 * 9.0
        spk = 0 * gl
        if spikes > 0:
            sp = cv2.GaussianBlur(small, (0, 0), sigmaX=70, sigmaY=0.8) + cv2.GaussianBlur(small, (0, 0), sigmaX=0.8, sigmaY=70)
            Mr = cv2.getRotationMatrix2D((cx / 2, cy / 2), 45, 1.0); sp2 = cv2.warpAffine(sp, Mr, (W // 2, H // 2))
            # only sources near the limb gap throw long spikes; weight by how point-like the source is
            pk = min(1.0, 0.004 / max(F, 1e-6)) ** 1.5
            spk = (sp * 2.2 + sp2 * 0.7) * spikes * pk
        expo = float(np.clip((0.004 / (F + 0.000002)) ** 0.9, 0.05, 150.0))
        gl = cv2.resize(gl, (W, H), interpolation=cv2.INTER_LINEAR) * glare * expo * 5.0 * (1 - 0.6 * moon)
        gl += np.minimum(cv2.resize(spk, (W, H), interpolation=cv2.INTER_LINEAR) * expo * 3.0, 0.7) * (1 - 0.92 * moon)
        img += gl[..., None] * np.array([1.0, 0.96, 0.88], F32)
        img += (P * 30 * min(max(expo, 0.2), 8.0))[..., None]
    return img, F


# ------------------------------------------------------------------------------------------------ proto-Earth
def molten_map():
    def make():
        fn = TEX + "/molten.npy"
        if os.path.exists(fn): return np.load(fn)
        Wm, Hm = 2048, 1024
        lon = ((np.arange(Wm, dtype=F32) + 0.5) / Wm - 0.5) * 2 * np.pi; lat = (0.5 - (np.arange(Hm, dtype=F32) + 0.5) / Hm) * np.pi
        LO, LA = np.meshgrid(lon, lat); P = np.stack([np.cos(LA) * np.cos(LO), np.cos(LA) * np.sin(LO), np.sin(LA)], -1)
        r = np.random.default_rng(12)
        def f3(scale, octs, ridged=False):
            out = np.zeros((Hm, Wm), F32); amp = 1.0; f = scale; tot = 0
            for o in range(octs):
                acc = np.zeros((Hm, Wm), F32)
                for _ in range(10):
                    k = r.standard_normal(3); k = k / np.linalg.norm(k) * f * r.uniform(0.7, 1.4)
                    acc += np.cos(P[..., 0] * k[0] + P[..., 1] * k[1] + P[..., 2] * k[2] + r.uniform(0, 6.28))
                acc /= 3.2
                out += amp * ((1 - np.abs(acc)) if ridged else acc); tot += amp; amp *= 0.58; f *= 2.1
            return out / tot
        plates = f3(5, 6, ridged=True)                  # ridged noise: bright along crack network
        big = f3(2.2, 3); fine = f3(40, 4)
        heat = np.clip((plates - 0.60) / 0.22, 0, 1) ** 2.2 * (0.55 + 0.6 * np.clip(big + 0.4, 0, 1)) + 0.55 * np.clip(big * 1.6 - 0.25, 0, 1) ** 1.5
        heat = np.clip(heat * (0.8 + 0.5 * fine), 0, 1.6)
        crust = 0.5 + 0.5 * fine
        a = np.dstack([heat, crust]).astype(F32); np.save(fn, a); return a
    return cached("molten", make)


def heat_col(h):
    """blackbody-ish ramp for 0..1.5"""
    h = np.clip(h, 0, 1.6)[..., None]
    return np.clip(np.concatenate([1.9 * h ** 0.75, 1.5 * h ** 1.9, 1.3 * h ** 3.6], -1), 0, 3)


def draw_molten(img, cx, cy, R, M, sun, heat=1.0, exposure=1.0, rock=(0.11, 0.085, 0.07), haze=1.0):
    g = _grid(cx, cy, R, max(6, R * 0.12))
    if g is None: return
    x0, y0, x1, y1, u, v = g
    rr = u * u + v * v; z = np.sqrt(np.clip(1 - rr, 0, 1)); sun = np.asarray(sun, F32)
    ndl = np.clip(u * sun[0] + v * sun[1] + z * sun[2], 0, 1); Mf = np.asarray(M, F32)
    bx = u * Mf[0, 0] + v * Mf[0, 1] + z * Mf[0, 2]; by = u * Mf[1, 0] + v * Mf[1, 1] + z * Mf[1, 2]; bz = u * Mf[2, 0] + v * Mf[2, 1] + z * Mf[2, 2]
    lat = np.arcsin(np.clip(bz, -1, 1)); lon = np.arctan2(by, bx)
    mm = samp(molten_map(), lat, lon)
    surf = np.asarray(rock, F32) * (mm[..., 1] * 1.4 * ndl ** 0.8 * exposure)[..., None] + heat_col(mm[..., 0] * heat) * (0.55 + 0.45 * z)[..., None]
    # hot hazy atmosphere toward the limb
    path = 1 / np.maximum(z, 0.08); ins = (1 - np.exp(-0.06 * path)) * haze
    surf = surf * (1 - 0.5 * ins[..., None]) + ins[..., None] * np.array([1.0, 0.42, 0.16], F32) * (0.25 + 0.6 * ndl[..., None])
    r = np.sqrt(rr); hpx = np.clip((r - 1) * R, 0, None); hs = max(2.0, R * 0.02)
    halo = (np.exp(-hpx / hs) * 0.5 + np.exp(-hpx / (hs * 4)) * 0.12) * haze
    a = np.clip((1 - r) * R + 0.5, 0, 1)[..., None]
    reg = img[y0:y1, x0:x1]; reg[:] = reg * (1 - a) + surf * a + (halo[..., None] * np.array([1.0, 0.40, 0.14], F32)) * (1 - a)


# ------------------------------------------------------------------------------------------------ sea + rocks
def sea(sky, yh, t, f, cxp=None, cam_h=1.0, base=(0.010, 0.016, 0.026), rough=1.0, speed=1.0, gain=1.0, horizon_col=None, stretch=3.2):
    """Replace everything below row yh by a rippled mirror of the sky (HDR in, HDR out)."""
    cxp = W / 2 if cxp is None else cxp
    T1 = cached("seaT1", lambda: tile_noise(1024, 6, 6, 0.6, 5)); T2 = cached("seaT2", lambda: tile_noise(1024, 6, 5, 0.62, 6))
    def grads(T): return np.dstack([np.roll(T, -1, 1) - np.roll(T, 1, 1), np.roll(T, -1, 0) - np.roll(T, 1, 0)]).astype(F32) * 24
    G1 = cached("seaG1", lambda: grads(T1)); G2 = cached("seaG2", lambda: grads(T2))
    yh = int(yh); n = H - yh
    if n <= 0: return sky
    ys = (np.arange(yh, H, dtype=F32) + 0.5 - yh)[:, None]; xs = (np.arange(W, dtype=F32) + 0.5 - cxp)[None, :]
    zd = cam_h * f / ys; xw = xs / f * zd
    slope = np.zeros((n, W, 2), F32)
    for G, sc_, vx, vz, amp in ((G1, 26.0, 0.9, 0.5, 1.0), (G2, 9.0, -0.5, 0.8, 0.9), (G1, 3.1, 0.25, -0.3, 0.8), (G2, 110.0, 1.6, 1.1, 0.5)):
        mx = (xw * sc_ + t * vx * speed * 14) % 1024; my = (np.broadcast_to(zd, (n, W)) * sc_ + t * vz * speed * 14) % 1024
        # fade scales that would alias at this distance
        px = zd * sc_ / f * (zd / cam_h)                     # texels per pixel along depth
        fade = np.clip(0.8 / np.maximum(px, 1e-3), 0, 1) ** 1.0
        slope += cv2.remap(G, mx.astype(F32), my.astype(F32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP) * (amp * fade)[..., None]
    slope *= 0.055 * rough
    xr = np.broadcast_to(np.arange(W, dtype=F32)[None, :], (n, W)) + slope[..., 0] * f * 1.0
    yr = (yh - ys - 0.5) - slope[..., 1] * f * stretch * (0.35 + 0.65 * np.clip(ys / (0.25 * f), 0, 1)) - np.abs(slope[..., 0]) * f * 0.6
    yr = np.clip(yr, 0, yh - 1)
    refl = cv2.remap(np.ascontiguousarray(sky[:yh]), xr.astype(F32), np.broadcast_to(yr, (n, W)).astype(F32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    cosi = np.clip(ys / np.sqrt(f * f + ys * ys) + slope[..., 1] * 0.8, 0.0, 1)
    Fr = 0.03 + 0.97 * (1 - cosi) ** 5
    out = sky.copy()
    wat = np.asarray(base, F32) * (1 - Fr[..., None]) + refl * Fr[..., None] * gain
    wat = cv2.GaussianBlur(wat, (0, 0), sigmaX=1.7, sigmaY=0.85)
    if horizon_col is not None:
        hz = np.exp(-ys / 5.0)[..., None]; wat = wat * (1 - 0.6 * hz) + np.asarray(horizon_col, F32) * 0.6 * hz
    out[yh:] = wat
    return out


def rocks(img, seed, y_base, height, light=(1.0, 0.75, 0.5), rim=0.9, tone=(0.020, 0.018, 0.018), scale=1.0, lava=0.0, x_shift=0.0, bias=None):
    """a rim-lit rocky shore silhouette with surface texture; y_base = lowest ridge level, height = relief in px"""
    def make():
        prof = pnoise(W * 2, 2, 7, 3 * scale, 0.55, seed, periodic_x=False)[0]
        prof2 = pnoise(W * 2, 2, 5, 40 * scale, 0.6, seed + 1, periodic_x=False)[0]
        texn = pnoise(W * 2, H // 2, 6, 14, 0.62, seed + 2, periodic_x=False, aspect=1.0)
        return prof, prof2, texn
    prof, prof2, texn = cached(("rocks", seed, scale), make)
    i0 = int(x_shift) % W
    p = prof[i0:i0 + W] + 0.22 * prof2[i0:i0 + W]
    if bias is not None: p = p + bias
    top = y_base - height * (0.5 + 0.9 * p)                                 # ridge line (px), per column
    yy = np.arange(H, dtype=F32)[:, None]
    depth = yy - top[None, :]
    m = np.clip(depth + 0.5, 0, 1)
    if m.max() <= 0: return
    tx = cv2.resize(texn[:, i0:i0 + W], (W, H), interpolation=cv2.INTER_LINEAR)
    gy = np.zeros_like(tx); gy[1:-1] = tx[2:] - tx[:-2]
    shade = np.clip(0.55 + 9.0 * -gy + 0.6 * tx, 0.05, 2.2)
    rimv = np.exp(-np.clip(depth, 0, None) / 5.0) * rim + np.exp(-np.clip(depth, 0, None) / 40.0) * rim * 0.25
    col = np.asarray(tone, F32) * shade[..., None] * (1 + 1.5 * np.exp(-np.clip(depth, 0, None) / 120.0))[..., None] + (rimv * shade)[..., None] * np.asarray(light, F32) * 0.16
    if lava > 0:
        cr = np.clip((1 - np.abs(cv2.resize(pnoise(W, H // 2, 5, 22, 0.6, seed + 5, periodic_x=False), (W, H))) * 9), 0, 1) ** 3 * np.clip(depth / 60, 0, 1)
        col += heat_col(cr * lava) * 0.5
    img *= (1 - m[..., None]); img += col * m[..., None]


# ------------------------------------------------------------------------------------------------ Blender plates
def plate(name):
    def make():
        a = cv2.imread(f"{SCR}/plates/{name}.png", cv2.IMREAD_UNCHANGED)
        a = a.astype(F32) / (65535 if a.dtype == np.uint16 else 255)
        if a.shape[2] == 4: a = a[..., [2, 1, 0, 3]]; a[..., :3] *= a[..., 3:4]
        else: a = np.dstack([a[..., ::-1], np.ones(a.shape[:2], F32)])
        return np.ascontiguousarray(a)
    return cached(("plate", name), make)


def plate_view(p, pcx, pcy, s, ox=0.0, oy=0.0):
    """plate point (pcx, pcy) lands on the frame centre (+ox, +oy) at scale s. Returns premultiplied RGBA frame."""
    M = np.array([[s, 0, W / 2 + ox - s * pcx], [0, s, H / 2 + oy - s * pcy]], F32)
    return cv2.warpAffine(p, M, (W, H), flags=cv2.INTER_AREA if s < 0.75 else cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def plate_pt(pt, pcx, pcy, s, ox=0.0, oy=0.0):
    return W / 2 + ox + s * (pt[0] - pcx), H / 2 + oy + s * (pt[1] - pcy)


def arrow(L, x0, y0, x1, y1, a=255, th=2, head=14):
    L.seg(x0, y0, x1, y1, a, th)
    ang = math.atan2(y1 - y0, x1 - x0)
    for s_ in (-1, 1):
        L.seg(x1, y1, x1 - head * math.cos(ang + s_ * 0.42), y1 - head * math.sin(ang + s_ * 0.42), a, th)
