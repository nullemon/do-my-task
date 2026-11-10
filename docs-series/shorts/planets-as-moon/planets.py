"""Lit planet discs for "What If Planets Replaced Our Moon?" (linear HDR, numpy / cv2).

Each body is rendered as a true 3-D (oblate) sphere seen by an orthographic ray per pixel, 2x supersampled in its
bounding box, then box-filtered down:
  - real equirectangular maps (Solar System Scope 2k/8k, CC BY 4.0, from NASA data), pre-filtered to the on-screen
    scale (no blurry up-scaling) plus a fine procedural detail layer
  - phase lighting from the Sun (below our horizon, behind-left of the camera): Lommel-Seeliger for the Moon / Mars,
    Minnaert limb darkening for the giants, soft terminator, atmospheric limb haze + a thin lit rim outside the limb
  - Jupiter: zonal winds (latitude-dependent drift) so the bands shear slowly; Great Red Spot turned to the lit side
  - Saturn: the real ring radial profile (8192 px, C ring to F ring), transparent, lit face, the globe's shadow on the
    rings and the rings' shadow on the globe; Uranus: its narrow ring system at the real radii (faint, dark)
Geometry: camera x right, y down, z forward (away from the viewer).
"""
import math, os
import numpy as np, cv2
from PIL import Image
from lib.core import f32, srgb_to_lin, fbm2, smooth

TEX = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/shorts-common/dl/sss"
SUN = np.array([-0.50, 0.16, -0.85]); SUN = SUN / np.linalg.norm(SUN)       # towards the Sun (camera frame)
D_MOON = 384400.0

# texture px -> ring radius (km): calibrated on the C-ring inner edge (px 434 = 74,658 km) and A-ring outer edge
# (px 7710 = 136,775 km); the B-ring outer edge then lands at px 5462 (texture: 5508).
RING_KM0, RING_KMPX = 74658.0 - 434 * 8.537, 8.537
# Uranus rings (km): 6, 5, 4, alpha, beta, eta, gamma, delta, lambda, epsilon; (radius, width km, optical depth-ish)
URANUS_RINGS = [(41837, 2, 0.3), (42234, 2, 0.3), (42571, 2, 0.3), (44718, 7, 0.4), (45661, 7, 0.35), (47176, 2, 0.15),
                (47627, 3, 0.5), (48300, 5, 0.5), (50023, 2, 0.1), (51149, 40, 0.8)]


def load_lin(name, size=None):
    im = Image.open(os.path.join(TEX, name)).convert("RGB")
    a = np.asarray(im, f32) / 255.0
    if size and size[0] < a.shape[1]: a = cv2.resize(a, size, interpolation=cv2.INTER_AREA)
    return srgb_to_lin(a)


def frame_of(pole):
    """rows = planet axes (X, Y=north pole, Z) in camera coordinates"""
    Y = np.asarray(pole, float); Y = Y / np.linalg.norm(Y)
    v = np.array([0.0, 0.0, -1.0])
    X = np.cross(Y, v); X = X / np.linalg.norm(X); Z = np.cross(X, Y)
    return np.stack([X, Y, Z])


def pole_vec(roll_deg, tip_deg):
    """north pole: 'up' on screen rotated by roll (clockwise +), tipped towards the viewer by tip"""
    r, b = math.radians(roll_deg), math.radians(tip_deg)
    return np.array([math.sin(r) * math.cos(b), -math.cos(r) * math.cos(b), -math.sin(b)])


class Body:
    def __init__(self, key, tex, Rp, pole, q=1.0, spin=0.0, lon0=0.0, model="giant", k=0.85, surf=1.0, haze=(0, 0, 0),
                 rim=(0, 0, 0), rings=None, winds=0.0, detail=0.05, ss=2, tint=(1, 1, 1), sat=1.0, gamma=1.0, seed=1):
        self.key, self.Rp, self.q, self.spin, self.lon0 = key, Rp, q, spin, lon0
        self.model, self.k, self.surf, self.winds, self.ss = model, k, surf, winds, ss
        self.haze, self.rim = np.array(haze, f32), np.array(rim, f32)
        self.M = frame_of(pole); self.rings = rings
        # texture filtered to the on-screen scale (2 px of map per rendered px at the disc centre at most)
        want = int(min(2 * math.pi * Rp * ss * 1.3, 8192)); want = max(want, 256)
        t = load_lin(tex, (want, want // 2)) * np.array(tint, f32)
        if sat != 1.0:
            y = t.mean(2, keepdims=True); t = np.clip(y + (t - y) * sat, 0, None)
        if gamma != 1.0: t = t ** gamma
        self.tex = t.astype(f32)
        h, w = self.tex.shape[:2]
        n = fbm2((min(h, 1024), min(w, 2048)), 300 + seed, 1.5)
        if model == "giant":                                         # streaky along the bands
            n = cv2.GaussianBlur(n, (0, 0), sigmaX=5, sigmaY=0.6); n = n / (n.std() + 1e-6)
        self.det = cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC) * detail
        self.ring_tex = None
        if rings == "saturn":
            r = np.asarray(Image.open(os.path.join(TEX, "8k_saturn_ring_alpha.png")).convert("RGBA"), f32).mean(0) / 255.0
            col = srgb_to_lin(np.clip(r[:, :3] * 1.9, 0, 1)) * np.array([1.10, 0.97, 0.82], f32)
            al = np.clip(r[:, 3] * 1.05, 0, 0.97)
            self.ring_tex = (col.astype(f32), al.astype(f32))
            self.r_in = RING_KM0 / 60268.0; self.r_out = (RING_KM0 + 8192 * RING_KMPX) / 60268.0
        elif rings == "uranus":
            rr = np.linspace(1.55, 2.05, 4096)
            al = np.zeros_like(rr)
            for rk, wk, tau in URANUS_RINGS:
                x = rk / 25559.0; wd = max(wk, 260) / 25559.0                    # widened to >= ~0.5 px so they show
                al += tau * np.exp(-((rr - x) / wd) ** 2)
            al = np.clip(al * 0.55, 0, 0.8)
            col = np.ones((len(rr), 3), f32) * np.array([0.30, 0.36, 0.42], f32)
            self.ring_tex = (col, al.astype(f32)); self.r_in, self.r_out = 1.55, 2.05

    # ------------------------------------------------------------------------------------------------
    def ring_sample(self, rho):
        col, al = self.ring_tex; n = len(al)
        i = np.clip((rho - self.r_in) / (self.r_out - self.r_in) * (n - 1), 0, n - 1)
        i0 = np.floor(i).astype(np.int32); i1 = np.minimum(i0 + 1, n - 1); f = (i - i0).astype(f32)
        a = al[i0] * (1 - f) + al[i1] * f
        c = col[i0] * (1 - f)[..., None] + col[i1] * f[..., None]
        inside = (rho > self.r_in) & (rho < self.r_out)
        return c, a * inside

    def ellipsoid_hit(self, o, d):
        q = self.q
        os_ = o.copy(); os_[..., 1] /= q; ds = d.copy(); ds[..., 1] /= q
        a = (ds * ds).sum(-1); b = (os_ * ds).sum(-1); c = (os_ * os_).sum(-1) - 1
        disc = b * b - a * c
        hit = disc > 0
        tt = (-b - np.sqrt(np.maximum(disc, 0))) / a
        reff = np.sqrt(np.maximum(1 - disc / a, 0))                      # perpendicular distance (scaled space)
        return hit, tt, reff

    def render(self, img, cx, cy, t, I=1.0, scale=1.0, ext=None, light=(1, 1, 1), extra_pad=0):
        """add the body into img (HxWx3 linear) centred at (cx, cy). Returns the coverage patch box for occlusion."""
        R = self.Rp * scale
        if R < 0.2: return
        H, W = img.shape[:2]
        outer = R * (self.r_out * 1.02 if self.rings else 1.0)
        P = self.M[1]                                                        # pole in camera frame
        px_ = max(outer * math.sqrt(max(1 - P[0] ** 2, 0)), R * 1.02) + 6 + R * 0.06 + extra_pad
        py_ = max(outer * math.sqrt(max(1 - P[1] ** 2, 0)), R * 1.02) + 6 + R * 0.06 + extra_pad
        x0, x1 = int(max(0, math.floor(cx - px_))), int(min(W, math.ceil(cx + px_)))
        y0, y1 = int(max(0, math.floor(cy - py_))), int(min(H, math.ceil(cy + py_)))
        if x1 <= x0 or y1 <= y0: return
        ss = self.ss if R > 1.5 else 4
        ys, xs = np.mgrid[0:(y1 - y0) * ss, 0:(x1 - x0) * ss].astype(f32)
        u = ((xs + 0.5) / ss + x0 - cx) / R; w = ((ys + 0.5) / ss + y0 - cy) / R
        M = self.M.astype(f32)
        o = np.stack([u, w, np.full_like(u, -10.0)], -1) @ M.T             # planet frame
        d = M[:, 2]                                                        # camera +z in planet frame
        dd = np.broadcast_to(d, o.shape)
        _, tt, reff = self.ellipsoid_hit(o, dd)
        cov0 = np.clip((1 - reff) * R * ss + 0.5, 0, 1).astype(f32)         # analytic limb anti-aliasing
        hit = cov0 > 0
        h = o + tt[..., None] * d
        s = (M @ SUN).astype(f32)
        rad = np.zeros(u.shape + (3,), f32); cov = np.zeros(u.shape, f32)
        if hit.any():
            n_ = h.copy(); n_[..., 1] /= self.q * self.q
            n_ /= np.linalg.norm(n_, axis=-1, keepdims=True) + 1e-9
            mu = np.clip(-(n_ @ d), 0.0, 1.0); mu0 = n_ @ s
            hs = h.copy(); hs[..., 1] /= self.q
            hs /= np.linalg.norm(hs, axis=-1, keepdims=True) + 1e-9
            lat = np.arcsin(np.clip(hs[..., 1], -1, 1)); lon = np.arctan2(hs[..., 0], hs[..., 2])
            lon = lon + self.lon0 - self.spin * t
            if self.winds:                                                  # zonal jets: bands drift at different rates
                lon = lon - self.winds * t * (np.sin(lat * 7.0) * 0.6 + np.sin(lat * 13.0 + 0.7) * 0.4) * np.cos(lat)
            th, tw_ = self.tex.shape[:2]
            mx = ((lon / (2 * np.pi) + 0.5) % 1.0 * tw_).astype(f32); my = np.clip((0.5 - lat / np.pi) * th - 0.5, 0, th - 1).astype(f32)
            alb = cv2.remap(self.tex, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
            dt = cv2.remap(self.det, mx * self.det.shape[1] / tw_, my * self.det.shape[0] / th, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
            alb = alb * (1 + dt)[..., None]
            if self.model == "rock":                                        # Lommel-Seeliger (flat-looking full Moon)
                m0 = np.maximum(mu0, 0)
                f = 2 * m0 / (m0 + np.maximum(mu, 0.02)) * smooth(-0.02, 0.06, mu0)
            else:                                                           # Minnaert limb darkening, soft terminator
                m0 = np.clip(mu0 + 0.04, 0, 1) / 1.04
                f = (m0 ** self.k) * np.maximum(mu, 0.05) ** (self.k - 1) * smooth(-0.06, 0.10, mu0)
            col = alb * f[..., None]
            # atmospheric limb haze (lit side) for the giants
            if self.haze.any():
                col = col + self.haze * ((1 - mu) ** 2.2 * smooth(-0.15, 0.4, mu0))[..., None]
            # ring shadow on the globe
            if self.rings:
                ts = -h[..., 1] / np.where(np.abs(s[1]) > 1e-6, s[1], 1e-6)
                p = h + ts[..., None] * s
                rho = np.sqrt(p[..., 0] ** 2 + p[..., 2] ** 2)
                _, a = self.ring_sample(rho)
                col = col * (1 - 0.92 * a * (ts > 0))[..., None]
            cov = cov0
            rad = col * cov[..., None] * self.surf
        # rings (in front of the globe where t_ring < t_globe; behind it hidden)
        if self.rings:
            dy = d[1] if abs(d[1]) > 1e-6 else 1e-6
            tr = -o[..., 1] / dy
            pr = o + tr[..., None] * d
            rho = np.sqrt(pr[..., 0] ** 2 + pr[..., 2] ** 2)
            rc, ra = self.ring_sample(rho)
            front = (cov0 < 0.5) | (tr < tt)
            ra = ra * front
            if ra.any():
                # globe's shadow on the rings
                hs_, ts_, _ = self.ellipsoid_hit(pr, np.broadcast_to(s, pr.shape))
                shad = hs_ & (ts_ > 0)
                lit_face = (np.sign(s[1]) == np.sign(-d[1]))
                lam = abs(s[1]) ** 0.35 * (1.0 if lit_face else 0.25)
                # unlit face / thin parts: some forward-scattered light (1 - a) a
                ring_rad = rc * (lam * (1 - shad * 0.95))[..., None] * (1.0 if lit_face else 1.0)
                ring_rad = ring_rad * self.surf * 1.35
                rad = rad * (1 - ra)[..., None] + ring_rad * ra[..., None]
                cov = cov * (1 - ra) + ra
        # thin lit rim outside the limb (atmosphere) on the sunward side
        if self.rim.any():
            sd = np.array([SUN[0], SUN[1]], f32); sd = sd / np.linalg.norm(sd)
            rr = np.sqrt(u * u + w * w)
            lit = np.clip((u * sd[0] + w * sd[1]) / (rr + 1e-6) * 1.3 - 0.05, 0, 1) ** 1.5
            rim = np.exp(-np.maximum(reff - 1.0, 0) * R / max(1.2, 0.010 * R)) * lit * (1 - cov0)
            rad = rad + (rim * (1 - cov))[..., None] * self.rim
        if ss > 1:
            sz = (x1 - x0, y1 - y0)
            rad = cv2.resize(rad, sz, interpolation=cv2.INTER_AREA); cov = cv2.resize(cov, sz, interpolation=cv2.INTER_AREA)
        rad = rad * np.array(light, f32) * I
        if ext is not None: rad = rad * ext[y0:y1, x0:x1]
        reg = img[y0:y1, x0:x1]
        img[y0:y1, x0:x1] = reg * (1 - cov[..., None]) + rad
        return (x0, x1, y0, y1, cov)


def small_moon(img, cx, cy, r, col, I=1.0, ext=None):
    """tiny moon (a few px): gibbous disc lit from the SUN side + glow"""
    H, W = img.shape[:2]
    pad = r * 9 + 14
    x0, x1, y0, y1 = int(max(0, cx - pad)), int(min(W, cx + pad)), int(max(0, cy - pad)), int(min(H, cy + pad))
    if x1 <= x0 or y1 <= y0: return
    ss = 4
    ys, xs = np.mgrid[0:(y1 - y0) * ss, 0:(x1 - x0) * ss].astype(f32)
    u = ((xs + 0.5) / ss + x0 - cx) / r; w = ((ys + 0.5) / ss + y0 - cy) / r
    rr2 = u * u + w * w
    inside = rr2 < 1
    z = -np.sqrt(np.clip(1 - rr2, 0, 1))
    mu0 = u * SUN[0] + w * SUN[1] + z * SUN[2]
    disc = inside * smooth(-0.05, 0.15, mu0)
    disc = cv2.resize(disc.astype(f32), (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(f32)
    dist = np.sqrt((xx + 0.5 - cx) ** 2 + (yy + 0.5 - cy) ** 2)
    glow = np.exp(-np.maximum(dist - r, 0) / (1.5 + r * 0.8)) * 0.6 + np.exp(-dist / (8 + r * 4)) * 0.10
    add = (disc * 3.0 + glow)[..., None] * np.array(col, f32) * I
    if ext is not None: add = add * ext[y0:y1, x0:x1]
    img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - disc[..., None]) + add
