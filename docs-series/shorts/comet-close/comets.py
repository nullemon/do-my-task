"""Physically inspired comet renderer for "What If Comets Passed as Close as the Moon?" (numpy, linear HDR).

A comet is drawn in a head-centred frame: a = distance along the anti-sunward axis, b = perpendicular distance.
  * coma     C2 Swan-band green glow, ~1/rho brightness profile (column density of a freely expanding gas, the
             classic Haser-like 1/rho look) cut off at the true coma radius; compressed on the sunward side
             (parabolic hood), stretched down-tail; optional expanding shells (Hale-Bopp's jets made spiral shells)
  * ion tail CO+ blue, straight along the anti-sun line, streamers (field-aligned rays, flowing outwards) and a
             periodic disconnection event (the tail snaps off and drifts away with a kink)
  * dust tail curved (older dust lags behind the orbit), yellow-white reflected sunlight, a fan of synchrones
             (dust released at the same moment lies along a straight-ish line) -> the striae of McNaught
  * sodium   a narrow yellow tail between the ion and dust tails (NEOWISE 2020, Hale-Bopp 1997)
Plus the nucleus loupe: the true shape (Halley's potato, 67P's duck) with sunward jets and outbursts.
"""
import math
import numpy as np, cv2
from lib.core import f32, smooth, fbm2

C2_GREEN = np.array([0.22, 1.00, 0.42], f32)
ION_BLUE = np.array([0.20, 0.48, 1.00], f32)
DUST = np.array([1.00, 0.84, 0.58], f32)
SODIUM = np.array([1.00, 0.66, 0.12], f32)

_ION_TEX = None
def ion_tex():
    global _ION_TEX
    if _ION_TEX is None:
        # smooth, fine, field-aligned filaments: a 1-D transverse comb of thin streamers (periodic in u), with only a
        # very slow brightness modulation along the tail (no speckle)
        r = np.random.default_rng(71); u = np.arange(128, dtype=f32)
        fil = np.zeros(128, f32)
        for _ in range(14):
            c = r.uniform(0, 128); wdt = r.uniform(1.4, 3.2); amp = r.uniform(0.3, 1.0)
            d = (u - c + 64) % 128 - 64; fil += amp * np.exp(-(d / wdt) ** 2)
        fil = 0.12 + 1.3 * fil / fil.max()
        slow = cv2.GaussianBlur(fbm2((128, 1024), 72, 2.0), (0, 0), sigmaX=1.5, sigmaY=40)
        slow = slow / (slow.std() + 1e-6)
        _ION_TEX = np.clip(fil[None, :] * (0.75 + 0.25 * slow.T), 0.05, 2.0).astype(f32)   # rows: along (v), cols: across (u)
    return _ION_TEX


def comet_field(C, X, Y, t, sc=1.0, grow=1.0, I=1.0):
    """HDR RGB of one comet sampled at full-frame coords X, Y (any grid). sc: spatial scale (bloom / implode),
    grow: 0..1 tail extension after the swap, I: brightness multiplier."""
    hx, hy = C["head"]
    th = math.radians(C["theta"]); Ax, Ay = math.cos(th), math.sin(th)
    dx = (X - hx) / sc; dy = (Y - hy) / sc
    a = dx * Ax + dy * Ay; b = -dx * Ay + dy * Ax
    rho = np.sqrt(dx * dx + dy * dy) + 1e-3
    Lg = 60 + 3200 * grow ** 1.4
    tmask = smooth(Lg, Lg * 0.75 - 20, a)
    out = np.zeros(X.shape + (3,), f32)
    Rc = C["Rc"]
    # ---- coma
    aa = np.where(a < 0, a * C.get("hood", 1.7), a * 0.72)
    re = np.sqrt(aa * aa + b * b) + 1e-3
    r0 = 0.22 * Rc + 2.0
    coma = (r0 / (re + r0)) * np.exp(-(re / Rc) ** 1.8) * 1.0 + np.exp(-re / (2.2 * Rc)) * 0.08
    if C.get("shells", 0) > 0:                                                    # expanding shells (sunward)
        sh = 0.5 + 0.5 * np.cos(re / Rc * 18 - t * 2.6 + 0.6 * np.arctan2(b, -a))
        coma = coma * (1 + C["shells"] * (sh ** 3 - 0.3) * smooth(0.1 * Rc, 0.3 * Rc, re) * smooth(Rc * 0.4, -Rc * 0.2, a))
    coma = coma + C.get("halo", 0.15) * np.exp(-(re / Rc) ** 2) * (1 + 0.06 * np.sin(re / Rc * 6 - t * 1.5))   # the visible extent of the coma
    breathe = 1 + 0.05 * math.sin(t * 2.1 + hx)
    out += coma[..., None] * C2_GREEN * (C["Ic"] * breathe)
    core = np.exp(-rho / (1.5 + 0.015 * Rc)) * 6.0 + np.exp(-rho / (5 + 0.06 * Rc)) * 1.2
    out += core[..., None] * np.array([0.75, 1.0, 0.85], f32) * C["Ic"] * C.get("core", 1.0)
    ap = np.maximum(a, 0)
    # ---- ion tail
    if C.get("Ii", 0) > 0:
        w = C["iw"] + 0.030 * ap
        Td = C.get("disc_T", 6.0); tau = (t + C.get("disc_ph", 0.0)) % Td
        ad = 40 + 520 * tau                                                       # disconnection front (px)
        kink = 28 * smooth(ad - 30, ad + 90, ap) * math.sin(0.7 * tau + 1)
        bb = b - kink - 6 * np.sin(ap / 260 - t * 0.9)                            # gentle rippling of the tail
        u = (bb / w) * 22 + 64; v = (ap * 0.05 - t * 22) % 1024                   # streamers flow outwards
        tex = cv2.remap(ion_tex().T.copy(), u.astype(f32), v.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        prof = np.exp(-(bb / w) ** 2 * 1.4)
        gap = 1 - 0.85 * np.exp(-((ap - ad) / 45) ** 2) * smooth(0.0, 0.4, tau)
        ion = prof * (0.25 + tex) * 1.6 * (C["iw"] / w) ** 0.45 / (1 + ap / 1100) * smooth(-Rc * 0.1, Rc * 0.4, a) * gap * tmask
        ion = ion + np.exp(-(bb / (w * 0.18 + 1.5)) ** 2) * 0.5 / (1 + ap / 500) * smooth(0, Rc * 0.3, a) * tmask * gap  # bright central ray
        out += ion[..., None] * ION_BLUE * C["Ii"]
    # ---- dust tail (curved fan of synchrones)
    if C.get("Id", 0) > 0:
        s = C["side"]
        u = b * s - C["bend"] * ap * ap / 1000.0
        r = np.sqrt(ap * ap + u * u) + 1e-3
        phi = np.arctan2(u, np.maximum(a, 1e-3)) + 0.025 * np.sin(r / 230 - t * 1.4)
        f0, f1 = C["fan"]
        x = (phi - f0) / (f1 - f0)
        fan = smooth(-0.15, 0.08, x) * smooth(1.18, 0.92, x)
        fan = fan * (0.55 + 0.45 * np.exp(-((x - 0.92) / 0.22) ** 2) + C.get("inner", 0.0) * np.exp(-(x / 0.18) ** 2))
        if C.get("striae", 0) > 0:                                                # synchrone bands: uneven spacing + strength
            q = C["nstr"] * x + C.get("skew", 0.0) * np.log1p(r / 300) - 0.05 * t
            q = q + 0.35 * np.sin(q * 0.73 + 1.3) + 0.2 * np.sin(q * 1.91 + 0.4)
            amp = 0.55 + 0.45 * np.sin(q * 2.37 + 0.8) * np.sin(q * 0.61 + 2.0)
            st = (0.5 + 0.5 * np.cos(2 * np.pi * q)) ** 2.0 * amp
            st = st * smooth(0.0, 900.0, r) + 0.5 * (1 - smooth(0.0, 900.0, r))        # striae appear away from the head
            fan = fan * (1 - C["striae"] + C["striae"] * 1.8 * st)
        r0 = C.get("r0", 700)
        rad = (1 / (1 + r / r0)) ** 1.25 * (0.6 + 0.4 * np.exp(-r / (0.15 * r0))) * smooth(-Rc * 0.05, Rc * 0.5, a)
        dust = fan * rad * tmask
        col = DUST if "dcol" not in C else np.array(C["dcol"], f32)
        out += dust[..., None] * col * C["Id"]
    # ---- sodium tail
    if C.get("Ina", 0) > 0:
        tn = th + C["side"] * math.radians(C.get("na_off", 9))
        nx, ny = math.cos(tn), math.sin(tn)
        an = dx * nx + dy * ny; bn = -dx * ny + dy * nx; anp = np.maximum(an, 0)
        wn = 6 + 0.012 * anp
        na = np.exp(-(bn / wn) ** 2) / (1 + anp / 700) * smooth(0, Rc * 0.5, an) * tmask
        out += na[..., None] * SODIUM * C["Ina"]
    return out * I


# ------------------------------------------------------------------------------------------------ nucleus (loupe)
def nucleus_mask(kind, XX, YY, t, spin):
    """soft mask of the true nucleus shape in loupe px coords (shape scaled to fit), rotating slowly"""
    c, s_ = math.cos(spin), math.sin(spin)
    X = XX * c + YY * s_; Y = -XX * s_ + YY * c
    if kind == "halley":                                                          # 15.3 x 7.2 km, lumpy potato
        ang = np.arctan2(Y, X)
        rr = np.sqrt((X / 1.0) ** 2 + (Y / 0.50) ** 2)
        bump = 1 + 0.07 * np.sin(3 * ang + 0.7) + 0.05 * np.sin(5 * ang + 2.1) + 0.03 * np.sin(9 * ang + 0.3)
        d = rr / bump - 1
        d = d - 0.10 * np.exp(-(((X - 0.15) / 0.18) ** 2 + ((Y + 0.5) / 0.15) ** 2))   # a waist (Halley's 'peanut' hint)
    else:                                                                         # 67P: big lobe 4.1 x 3.3, small lobe 2.6 x 2.3 km
        k = 1 / 3.2                                                                # loupe units per km
        d1 = np.sqrt(((X + 0.25) / (2.05 * k)) ** 2 + ((Y - 0.15) / (1.65 * k)) ** 2) - 1
        Xr = (X - 0.47) * math.cos(0.6) + (Y + 0.45) * math.sin(0.6); Yr = -(X - 0.47) * math.sin(0.6) + (Y + 0.45) * math.cos(0.6)
        d2 = np.sqrt((Xr / (1.30 * k)) ** 2 + (Yr / (1.15 * k)) ** 2) - 1
        kk = 0.06
        d = -kk * np.log(np.exp(-d1 / kk) + np.exp(-d2 / kk))                       # smooth union -> the 'neck'
        ang = np.arctan2(Y, X)
        d = d + 0.03 * np.sin(7 * ang + 1.0)
    return d


def nucleus_loupe(kind, r, R, t, sun_dir, jets=1.0, outburst=0.0):
    """HDR content (2r x 2r) of the magnifier: inner green coma, lit dark nucleus, sunward jets, outburst puff"""
    g = np.arange(2 * r, dtype=f32) + 0.5 - r
    XX, YY = np.meshgrid(g, g)
    size = 0.62 * R
    spin = 0.35 * math.sin(t * 0.25) + 0.2
    d = nucleus_mask(kind, XX / size, YY / size, t, spin)
    m = smooth(0.02, -0.02, d)
    h = cv2.GaussianBlur(np.clip(-d, 0, 0.6).astype(f32), (0, 0), max(R * 0.04, 1.0))
    gy, gx = np.gradient(h)
    n = np.stack([-gx * 18, -gy * 18, np.ones_like(gx)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    sx, sy = sun_dir; L = np.array([sx, sy, 0.55], f32); L /= np.linalg.norm(L)
    lam = np.clip(n @ L, 0, 1)
    rough = 0.75 + 0.25 * cv2.resize(fbm2((64, 64), 13, 2.2), (2 * r, 2 * r))
    alb = 0.045                                                                   # darker than coal
    body = m * (lam ** 1.4 * rough * alb * 14.0 + 0.004)
    out = body[..., None] * np.array([1.0, 0.95, 0.88], f32)
    rr = np.sqrt(XX * XX + YY * YY)
    out += ((np.exp(-rr / (0.55 * R)) * 0.35 + np.exp(-rr / (1.4 * R)) * 0.12) * (1 - 0.8 * m))[..., None] * C2_GREEN
    # jets: narrow fans from sunlit active areas, curving away as the nucleus turns
    jm = np.zeros((2 * r, 2 * r), f32)
    base = math.atan2(sy, sx)
    rs = np.random.default_rng(3 if kind == "halley" else 4)
    for j in range(6 if kind == "halley" else 8):
        a0 = base + rs.uniform(-1.0, 1.0) + 0.25 * math.sin(t * 0.8 + j)
        x0, y0 = -1.0, -1.0
        for k in range(60):                                                        # walk out from the limb
            px, py = math.cos(a0) * k * size * 0.02, math.sin(a0) * k * size * 0.02
            if nucleus_mask(kind, np.array([[px / size]], f32), np.array([[py / size]], f32), t, spin)[0, 0] > 0:
                x0, y0 = px, py; break
        if x0 == -1.0: continue
        L_ = R * rs.uniform(0.7, 1.2); I_ = rs.uniform(0.5, 1.0) * (0.75 + 0.25 * math.sin(t * 3 + j * 2))
        pts = []
        for u in np.linspace(0, 1, 30):
            cur = 0.35 * u * u * (1 if j % 2 else -1)
            ang = a0 + cur
            pts.append((x0 + math.cos(ang) * L_ * u + r, y0 + math.sin(ang) * L_ * u + r, u))
        for (xa, ya, ua), (xb, yb, ub) in zip(pts, pts[1:]):
            wth = int(2 + 10 * ua)
            cv2.line(jm, (int(xa * 4), int(ya * 4)), (int(xb * 4), int(yb * 4)), float(I_ * (1 - ua) ** 1.3), wth, cv2.LINE_AA, shift=2)
    jm = cv2.GaussianBlur(jm, (0, 0), 2.2) * 1.4 + cv2.GaussianBlur(jm, (0, 0), 7) * 0.8
    out += (jm * jets * (1 - 0.7 * m))[..., None] * np.array([0.80, 1.0, 1.0], f32)
    if outburst > 0:                                                              # an outburst: a bright expanding puff
        ox, oy = sx * size * 0.45, sy * size * 0.45
        dd = np.sqrt((XX - ox) ** 2 + (YY - oy) ** 2)
        Rb = R * (0.1 + 0.9 * outburst)
        puff = np.exp(-((dd - Rb * 0.6) / (Rb * 0.45)) ** 2) * (1 - outburst) ** 1.2 * 1.6 + np.exp(-dd / (Rb * 0.5)) * (1 - outburst) * 2.0
        cone = np.clip(((XX - ox) * sx + (YY - oy) * sy) / (dd + 1e-3), 0, 1) ** 1.5
        out += (puff * (0.3 + 0.7 * cone) * (1 - 0.8 * m))[..., None] * np.array([1.0, 0.97, 0.85], f32)
    return out
