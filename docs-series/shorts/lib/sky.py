"""Sky layer for ground-level Shorts (linear HDR).
 SkyCam      pinhole model anchored on the foreground horizon row: pixel -> (elevation, direction)
 day_sky     Rayleigh gradient (deep zenith blue -> pale horizon, (1+cos^2) phase), Mie aureole around the sun, faint cirrus
 sun_disc    0.53 deg disc with limb darkening + HDR core for bloom; lens_flare: subtle ghosts on the sun-centre axis
 StarSky     procedural star plate (power-law magnitudes, black-body colours, structured Milky Way with dust lanes);
             faint stars + Milky Way are a static plate, the ~2500 brightest are splatted per frame with scintillation
             that grows towards the horizon (airmass); horizon extinction + airglow
 lens_view   telescope view of a point-mass lens: inverse ray-shooting with beta = theta - thetaE^2 theta/|theta|^2,
             point sources lensed then blurred by seeing (PSF applied in the image plane)
"""
import os, math
import numpy as np, cv2
from .core import f32, smooth, fbm2, bbcolor, noise1, splat, CACHE


class SkyCam:
    def __init__(self, W, H, horizon, f):
        self.W, self.H, self.hz, self.f = W, H, horizon, f
        yy, xx = np.mgrid[0:H:2, 0:W:2].astype(f32) + 0.5          # half-res grid for smooth fields
        self.dx = (xx * 1.0 + 0.5 - W / 2) / f; self.dz = (horizon - yy - 0.5) / f
        inv = 1 / np.sqrt(self.dx ** 2 + 1 + self.dz ** 2)
        self.el = np.arcsin(np.clip(self.dz * inv, -1, 1)).astype(f32)
        self.inv = inv.astype(f32)

    def dir_of(self, x, y):
        d = np.array([(x - self.W / 2) / self.f, 1.0, (self.hz - y) / self.f]); return d / np.linalg.norm(d)

    def gamma(self, sx, sy):
        s = self.dir_of(sx, sy)
        c = np.clip((self.dx * s[0] + s[1] + self.dz * s[2]) * self.inv, -1, 1)
        return np.arccos(c).astype(f32), c.astype(f32)

    def up(self, a):
        return cv2.resize(a, (self.W, self.H), interpolation=cv2.INTER_LINEAR)


_cir = {}
def day_sky(cam, sx, sy, t, sun=1.0, cirrus=0.25):
    """daytime sky radiance (linear). sun = 0..1 scales all scattered light"""
    el = np.maximum(cam.el, 0); gam, cg = cam.gamma(sx, sy)
    zen = np.array([0.016, 0.095, 0.48], f32); hor = np.array([0.36, 0.55, 0.82], f32)
    k = np.exp(-el / 0.16)[..., None]
    phase = (0.62 + 0.38 * (1 + cg * cg) / 2)[..., None]
    ray = (zen * (1 - k) + hor * k) * phase
    ray *= (1 + 0.35 * np.exp(-el / 0.05))[..., None]
    mie = (1.4 * np.exp(-gam / 0.018) + 0.40 * np.exp(-gam / 0.06) + 0.10 * np.exp(-gam / 0.2) + 0.025 * np.exp(-gam / 0.7))[..., None] \
        * np.array([1.0, 0.90, 0.74], f32)
    sky = ray + mie
    if cirrus > 0:
        if "c" not in _cir: _cir["c"] = np.clip(fbm2((512, 1024), 92, 2.4) * 0.5 + 0.3, 0, 1) ** 1.8
        u = cam.dx / (cam.dz + 0.35) * 260 + t * 2.0; v = 1.0 / (cam.dz + 0.35) * 120
        ci = cv2.remap(_cir["c"], (u % 1024).astype(f32), (v % 512).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        ci = np.clip(ci * 2.2 - 0.75, 0, 1) ** 1.5 * smooth(0.0, 0.25, el) * cirrus
        cc = np.array([0.80, 0.84, 0.92], f32) + np.array([1.0, 0.85, 0.65], f32) * (np.exp(-gam / 0.25) * 1.5)[..., None]
        sky = sky * (1 - ci[..., None] * 0.5) + cc * ci[..., None] * 0.55
    return cam.up(sky * sun)


def sun_disc(img, sx, sy, r, power=1.0):
    """limb-darkened disc (radius r px) with an HDR core so bloom gives the glare"""
    if power <= 0: return
    def fn(d, dx, dy):
        mu = np.sqrt(np.clip(1 - (d / r) ** 2, 0, 1))
        limb = 0.4 + 0.6 * mu
        disc = np.clip(r - d + 0.5, 0, 1) * limb * 220.0
        aure = 3.0 * np.exp(-d / (r * 1.4)) + 0.35 * np.exp(-d / (r * 5))
        return ((disc + aure) * power)[..., None] * np.array([1.0, 0.95, 0.86], f32)
    splat(img, sx, sy, r * 30, fn)


def lens_flare(img, sx, sy, power=1.0, seed=3):
    """subtle optical ghosts along the line sun -> frame centre, plus faint 6-blade diffraction spikes"""
    if power <= 0: return
    H, W = img.shape[:2]; cx, cy = W / 2, H / 2
    ghosts = [(-0.35, 26, (0.35, 0.55, 1.0), 0.010), (-0.62, 60, (0.55, 1.0, 0.6), 0.006), (-0.95, 120, (1.0, 0.6, 0.4), 0.004),
              (0.45, 14, (0.8, 0.6, 1.0), 0.012), (-1.3, 44, (0.5, 0.8, 1.0), 0.007), (-1.75, 180, (1.0, 0.85, 0.6), 0.0025)]
    sc = W / 1080
    for k, rad, col, a in ghosts:
        gx = cx + (sx - cx) * k; gy = cy + (sy - cy) * k; R = rad * sc
        def fn(d, dx, dy, R=R, a=a, col=col):
            ang = np.arctan2(dy, dx); poly = np.cos(math.pi / 6) / np.cos(((ang + 0.3) % (math.pi / 3)) - math.pi / 6)   # hexagon
            e = d / (R * poly)
            ring = smooth(1.02, 0.86, e) * (0.55 + 0.45 * smooth(0.5, 1.0, e))
            return (ring * a * power)[..., None] * np.array(col, f32)
        splat(img, gx, gy, R * 1.3, fn)
    def spikes(d, dx, dy):
        ang = np.arctan2(dy, dx)
        s = np.zeros_like(d)
        for i in range(6):
            a0 = 0.35 + i * math.pi / 3
            off = np.abs(np.sin(ang - a0)) * d
            s += np.exp(-off / 1.2) * np.exp(-d / (140 * sc)) * (np.cos(ang - a0) > 0)
        return (s * 0.18 * power)[..., None] * np.array([1.0, 0.95, 0.88], f32)
    splat(img, sx, sy, 520 * sc, spikes)


# ---------------------------------------------------------------------------------------------- stars
SKW, SKH = 4096, 2560
class StarSky:
    def __init__(self, seed=42, n_bright=2600):
        p = os.path.join(CACHE, f"stars_{seed}.npz")
        if not os.path.exists(p): self._build(p, seed, n_bright)
        z = np.load(p)
        self.plate = z["plate"].astype(f32); self.bx, self.by, self.bf, self.bc = z["bx"], z["by"], z["bf"], z["bc"]
        r = np.random.default_rng(seed + 1)
        self.ph = r.uniform(0, 1000, len(self.bx)).astype(f32)

    def _build(self, p, seed, n_bright):
        r = np.random.default_rng(seed)
        yy, xx = np.mgrid[0:SKH, 0:SKW].astype(f32)
        ang = math.radians(-58); cx0, cy0 = SKW * 0.52, SKH * 0.40
        along = ((xx - cx0) * math.cos(ang) + (yy - cy0) * math.sin(ang)) / SKW
        across = (-(xx - cx0) * math.sin(ang) + (yy - cy0) * math.cos(ang)) / SKH
        n1 = fbm2((SKH, SKW), 1, 2.6); n2 = fbm2((SKH, SKW), 2, 2.0); n3 = fbm2((SKH, SKW), 3, 2.1); n4 = fbm2((SKH, SKW), 4, 2.9)
        warp = across + 0.03 * n4 + 0.010 * n1
        width = 0.085 * (1 + 0.9 * np.exp(-((along + 0.10) / 0.14) ** 2))
        band = np.exp(-(warp / width) ** 2) * (0.5 + 0.8 * np.exp(-((along + 0.10) / 0.25) ** 2))
        halo = np.exp(-np.abs(warp) / 0.3) * 0.06
        clouds = np.clip(0.7 + 0.45 * n1 + 0.22 * n2, 0.06, 2.3)
        dust = np.clip(1.25 - np.abs(n1 * 0.9 + n2 * 0.5 + 0.2) * 1.25, 0, 1) ** 1.6 * np.exp(-((warp + 0.006) / (width * 0.45)) ** 2)
        dust += np.clip(n4 * 0.6 + n2 * 0.5 - 0.35, 0, 1) * np.exp(-(warp / (width * 0.85)) ** 2) * 0.9
        dust = np.clip(dust, 0, 1)
        glow = (band * clouds + halo) * (1 - 0.86 * dust)
        warm = np.exp(-((along + 0.10) / 0.18) ** 2) * np.exp(-(warp / (width * 0.9)) ** 2)
        colc = np.array([0.62, 0.74, 1.0], f32) * (1 - warm[..., None]) + np.array([1.0, 0.82, 0.58], f32) * warm[..., None]
        sky = glow[..., None] * colc * 0.10
        grain = np.clip(n3 * 0.5 + 0.5, 0, 2) ** 2
        sky *= (0.70 + 0.45 * grain)[..., None]
        dens = 0.22 + 2.6 * band * (1 - 0.8 * dust) + halo * 3
        nst = 160000
        pdf = dens.ravel().astype(np.float64); pdf /= pdf.sum()
        idx = r.choice(SKW * SKH, nst, p=pdf)
        sy = idx // SKW + r.uniform(0, 1, nst); sx = idx % SKW + r.uniform(0, 1, nst)
        flux = 0.0075 * r.uniform(0, 1, nst) ** (-1 / 1.05); flux = np.minimum(flux, 70)
        temps = np.clip(r.lognormal(np.log(5600), 0.38, nst), 2800, 22000)
        cols = np.stack([bbcolor(T) for T in np.linspace(2800, 22000, 64)])
        sc_ = 0.45 + 0.55 * cols[np.clip(((temps - 2800) / (22000 - 2800) * 63).astype(int), 0, 63)]
        order = np.argsort(-flux); bright = order[:n_bright]; faint = order[n_bright:]
        acc = np.zeros((SKH + 2, SKW + 2, 3), f32)
        x0 = np.floor(sx[faint]).astype(int); y0 = np.floor(sy[faint]).astype(int)
        fx = (sx[faint] - x0)[:, None]; fy = (sy[faint] - y0)[:, None]
        val = (flux[faint, None] * sc_[faint]).astype(f32)
        for dy, dx, wgt in ((0, 0, (1 - fx) * (1 - fy)), (0, 1, fx * (1 - fy)), (1, 0, (1 - fx) * fy), (1, 1, fx * fy)):
            np.add.at(acc, (np.clip(y0 + dy, 0, SKH), np.clip(x0 + dx, 0, SKW)), val * wgt)
        stars = cv2.GaussianBlur(acc[:SKH, :SKW], (0, 0), 0.6) * 2.6
        plate = (sky + stars).astype(np.float16)
        np.savez(p, plate=plate, bx=sx[bright].astype(f32), by=sy[bright].astype(f32), bf=flux[bright].astype(f32), bc=sc_[bright].astype(f32))

    def render(self, cam, t, cx=SKW * 0.5, cy=SKH * 0.55, rot=0.0, gain=1.0, twinkle=1.0, air=1.0, shift=(0.0, 0.0), plate_gain=0.5, star_gain=1.0):
        """night sky radiance for the full frame. plate pixel (cx, cy) sits at the frame point (W/2, horizon - 0.45 H)"""
        W, H = cam.W, cam.H
        ax, ay = W / 2 + shift[0], cam.hz - 0.45 * H + shift[1]
        M = cv2.getRotationMatrix2D((0, 0), rot, 1.0)
        M[0, 2] = cx - (M[0, 0] * ax + M[0, 1] * ay); M[1, 2] = cy - (M[1, 0] * ax + M[1, 1] * ay)
        img = cv2.warpAffine(self.plate, M, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_WRAP) * plate_gain
        # bright stars: plate -> frame
        Mi = cv2.invertAffineTransform(M)
        fx = Mi[0, 0] * self.bx + Mi[0, 1] * self.by + Mi[0, 2]; fy = Mi[1, 0] * self.bx + Mi[1, 1] * self.by + Mi[1, 2]
        sel = (fx > -4) & (fx < W + 4) & (fy > -4) & (fy < cam.hz + 4)
        fx, fy, fl, col, ph = fx[sel], fy[sel], self.bf[sel], self.bc[sel], self.ph[sel]
        el = np.maximum((cam.hz - fy) / cam.f, 0.0)
        airm = 1.0 / (np.sin(np.minimum(el, 1.5)) + 0.06)                    # crude airmass
        sig = twinkle * np.clip(0.10 * airm ** 0.9, 0.08, 0.9)
        n = np.sin(t * 13.1 + ph) * 0.5 + np.sin(t * 23.7 + ph * 1.7) * 0.3 + np.sin(t * 37.3 + ph * 2.3) * 0.2
        fac = np.exp(sig * n * 1.6 - 0.5 * sig * sig)
        fl = fl * fac * np.exp(-0.12 * (airm - 1) * air)
        # chromatic twinkle near the horizon
        cshift = (np.sin(t * 17.0 + ph * 3.1) * np.clip(sig - 0.25, 0, 0.6))[:, None] * np.array([0.5, -0.1, -0.5], f32)
        col = np.clip(col * (1 + cshift), 0, 2)
        acc = np.zeros((H + 2, W + 2, 3), f32)
        x0 = np.floor(fx).astype(int); y0 = np.floor(fy).astype(int); ux = (fx - x0)[:, None]; uy = (fy - y0)[:, None]
        val = (fl[:, None] * col).astype(f32)
        for dy, dx, wgt in ((0, 0, (1 - ux) * (1 - uy)), (0, 1, ux * (1 - uy)), (1, 0, (1 - ux) * uy), (1, 1, ux * uy)):
            np.add.at(acc, (np.clip(y0 + dy, 0, H + 1), np.clip(x0 + dx, 0, W + 1)), val * wgt)
        acc = acc[:H, :W]
        stars = cv2.GaussianBlur(acc, (0, 0), 0.65) * 2.6
        big = acc * (acc.max(2, keepdims=True) > 2.0)
        stars += cv2.GaussianBlur(big, (0, 0), 1.6) * 1.6 + cv2.GaussianBlur(big, (0, 0), 5.0) * 1.2
        img = img + stars * star_gain
        # extinction + airglow near the horizon
        el2 = np.maximum(cam.el, 0)
        ext = cam.up(1 - air * 0.8 * np.exp(-el2 / 0.06))
        glow = cam.up(np.exp(-el2 / 0.12)[..., None] * np.array([0.0035, 0.0055, 0.0090], f32) * air)
        return (img * ext[..., None] + glow) * gain


# ---------------------------------------------------------------------------------------------- lensing
class LensField:
    """Background sky around a point-mass lens, in arcsec.
    Stars are true point sources: each has two images theta+- = beta_hat (u +- sqrt(u^2+4))/2 thetaE with magnifications
    mu+- = (u^2+2)/(2u sqrt(u^2+4)) +- 1/2, splatted with the seeing PSF (no fake smearing of stars into rings).
    Faint galaxies are extended sources: rendered by inverse ray-shooting (surface brightness is conserved), so a galaxy
    close to alignment is stretched into arcs / an Einstein ring."""
    def __init__(self, half=230.0, res=0.15, n=300, seed=7, hero=(), galaxies=(), n_gal=10):
        self.half, self.res = half, res
        r = np.random.default_rng(seed)
        xs = r.uniform(-half, half, n); ys = r.uniform(-half, half, n)
        fl = 0.5 * r.uniform(0, 1, n) ** (-1 / 1.15); fl = np.minimum(fl, 40)
        temps = np.clip(r.lognormal(np.log(5200), 0.35, n), 3000, 15000)
        for hx, hy, hf, hT in hero:
            xs = np.append(xs, hx); ys = np.append(ys, hy); fl = np.append(fl, hf); temps = np.append(temps, hT)
        self.sx, self.sy, self.sf = xs.astype(f32), ys.astype(f32), fl.astype(f32)
        self.sc = np.stack([0.5 + 0.5 * bbcolor(T) for T in temps]).astype(f32)
        N = int(2 * half / res); self.N = N
        tex = np.zeros((N, N, 3), f32)
        gals = list(galaxies) + [(r.uniform(-half, half), r.uniform(-half, half), r.uniform(1.5, 4), r.uniform(0.3, 0.9),
                                  r.uniform(0, 180), r.uniform(0.02, 0.06)) for _ in range(n_gal)]
        for gx, gy, rad, q, pa, br in gals:                       # (x, y, radius", axis ratio, PA deg, brightness)
            px, py = (gx + half) / res, (gy + half) / res; R = rad / res
            ca, sa = math.cos(math.radians(pa)), math.sin(math.radians(pa))
            col = np.array([1.0, 0.86, 0.70], f32) if br > 0.05 else np.array([0.80, 0.86, 1.0], f32)
            def fn(d, dx, dy, R=R, q=q, ca=ca, sa=sa, br=br, col=col):
                u = (dx * ca + dy * sa); v = (-dx * sa + dy * ca) / q
                rr = np.sqrt(u * u + v * v) / R
                return (br * np.exp(-3.0 * (rr ** 0.6 - 1)) / 20.0 * (rr < 4))[..., None] * col
            splat(tex, px, py, R * 4, fn)
        self.tex = tex
        self.sky_bg = np.array([0.0004, 0.0005, 0.0008], f32)

    def view(self, size, field, thetaE, lens_off, seeing=0.9, ss=2, star_gain=1.0):
        """size px square image, `field` arcsec wide, centred on the lens. lens_off = lens position in the
        star field's frame (arcsec); animate it for the relative drift."""
        n = size * ss
        g = (np.arange(n, dtype=f32) + 0.5) / n * field - field / 2
        tx, ty = np.meshgrid(g, g)
        k = 1 - thetaE ** 2 / (tx * tx + ty * ty + 1e-6)
        bx = tx * k + lens_off[0]; by = ty * k + lens_off[1]
        mx = ((bx + self.half) / self.res - 0.5).astype(f32); my = ((by + self.half) / self.res - 0.5).astype(f32)
        img = cv2.remap(self.tex, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        img = cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA)
        px = field / size
        img = cv2.GaussianBlur(img, (0, 0), seeing / px * 0.6)
        # point sources: two images each
        bxs = self.sx - lens_off[0]; bys = self.sy - lens_off[1]
        b = np.sqrt(bxs ** 2 + bys ** 2) + 1e-6; u = b / thetaE
        sq = np.sqrt(u * u + 4)
        mu_c = (u * u + 2) / (2 * u * sq)
        pts = []
        for sgn in (1, -1):
            th = (u + sgn * sq) / 2 * thetaE                          # signed radius along beta_hat
            ix = bxs / b * th; iy = bys / b * th
            mu = np.abs(mu_c + sgn * 0.5)
            pts.append((ix, iy, self.sf * mu))
        acc = np.zeros((size + 2, size + 2, 3), f32)
        for ix, iy, f in pts:
            fx = ix / px + size / 2; fy = iy / px + size / 2
            ok = (fx > 0) & (fx < size) & (fy > 0) & (fy < size) & (f > 1e-3)
            fx, fy, f, c = fx[ok], fy[ok], f[ok], self.sc[ok]
            x0 = np.floor(fx).astype(int); y0 = np.floor(fy).astype(int); ux = (fx - x0)[:, None]; uy = (fy - y0)[:, None]
            val = f[:, None] * c
            for dy, dx, w in ((0, 0, (1 - ux) * (1 - uy)), (0, 1, ux * (1 - uy)), (1, 0, (1 - ux) * uy), (1, 1, ux * uy)):
                np.add.at(acc, (y0 + dy, x0 + dx), val * w)
        acc = acc[:size, :size]
        sig = seeing / px
        st = cv2.GaussianBlur(acc, (0, 0), sig) * (2 * math.pi * sig * sig) ** 0.5 * 0.35
        st += cv2.GaussianBlur(acc, (0, 0), sig * 4) * 0.02
        return img + st * star_gain + self.sky_bg
