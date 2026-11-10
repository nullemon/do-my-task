"""WHAT IF THE SUN BECAME A BLACK HOLE? — stylized VFX version (locked tripod shot of the park, reference-style spectacle).
Beats (timed to the existing voice):
  day      giant chromatic light beams fanning from the Sun, slowly rotating and flaring, tinting the whole scene
  collapse beams spiral inward and turn hot orange/red/violet, the Sun swells and wobbles, implodes; shockwave + white flash
  night    the sky crashes to deep indigo (park stays readable), stars, lamps on
  hole     a huge black hole where the Sun was: black core, blazing white-violet photon ring, Interstellar-style lensed disk
           (front band + arches over and under), infalling spiral gas, the starfield lensed and swirling around it, pulses, flares
  cold     a blue-white frost wave sweeps across the park with sparkles, drifting mist, big temperature readout
  end      the hole flares to a full white-out (loops)
Usage: /home/user/ttsenv/bin/python short_vfx.py vert|wide [t1,t2,...]
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import short as A
from short import SCR, DUR, FPS, LN, WORDS, wt, T_NOW, T_OUT, temp_c, day_of
import numpy as np, cv2
from PIL import Image
from lib.core import f32, ease, ramp, smooth, noise1, splat, fbm2, lum
from lib.post import bloom, tonemap, finish, Encoder
from lib.text import hud_text, font

# ------------------------------------------------------------------------------------------------ timeline
T_COL = LN["then"]["start"]                    # beams start spiralling in
T_SWELL1 = A.wt("then", "JUST")                # swelling peak -> implosion
T_IMPL = T_OUT - 0.14                          # implosion complete
T_BH0, T_BH1 = T_OUT + 0.9, T_OUT + 4.2        # black hole forms
T_COLD = A.wt("cold", "COLD") - 0.3
T_WEEK, T_YEAR = A.wt("cold", "−18°C"), A.wt("cold", "−73°C")
T_LAST = A.T_LAST
T_WHITE = T_LAST + 0.15                         # final flare -> white-out
FLARES = [A.wt("orbit", "UNCHANGED"), A.wt("bh", "6 KM"), A.wt("scope", "BENDING"), A.wt("end", "FROZEN")]


def palette(x):
    """smooth spectral palette, x in [0, 1) -> saturated rainbow (linear RGB)"""
    x = x[..., None] if np.ndim(x) else x
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (x - np.array([0.0, 0.33, 0.67], f32)))
    return (c ** 2.2).astype(f32)


HOT = np.array([[1.0, 0.55, 0.12], [1.0, 0.18, 0.08], [0.75, 0.18, 1.0], [1.0, 0.85, 0.5]], f32)


class VFX(A.Scene):
    def __init__(self, vertical=True):
        super().__init__(vertical)
        L = self.L; W, H = L.W, L.H
        self.C = (560.0, 560.0) if vertical else (1240.0, 300.0)     # Sun / black hole centre
        self.Rs = 104.0 if vertical else 92.0                          # shadow radius (px) at full size
        hw, hh = W // 2, H // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.dx = xx - self.C[0]; self.dy = yy - self.C[1]
        self.d = np.sqrt(self.dx ** 2 + self.dy ** 2) + 1e-3; self.phi = np.arctan2(self.dy, self.dx)
        r = np.random.default_rng(5)
        n = 6
        self.beams = [dict(a=i * 2 * np.pi / n + r.uniform(-0.3, 0.3), w=r.uniform(0.17, 0.30), I=r.uniform(0.8, 1.2), hue=r.uniform(0, 1),
                           rainbow=bool(i % 3 != 2), ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(n)]
        self.beams.sort(key=lambda b: b["a"])
        # night foreground: readable deep-blue grade of the photo (flattened shadows)
        f = self.fg.flat; y = lum(f)[..., None]
        self.fg_night = ((f * 0.35 + y * 0.65) * np.array([0.16, 0.20, 0.42], f32)).astype(f32)
        self.disk_tex = np.clip(fbm2((256, 1024), 31, 2.2) * 0.35 + fbm2((256, 1024), 32, 1.2) * 0.25 + 0.75, 0.15, 2.0).astype(f32)
        self.mist = np.clip(fbm2((512, 1024), 41, 2.6) * 0.5 + 0.45, 0, 1).astype(f32)
        self.noise_x = cv2.resize(fbm2((128, 128), 51, 2.4), (W, H), interpolation=cv2.INTER_CUBIC)
        yyf, xxf = np.mgrid[0:H, 0:W].astype(f32)
        self.xx, self.yy = xxf, yyf

    def up(self, a):
        return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    # -------------------------------------------------------------------------------------------- day + collapse
    def sky_day(self, t, level=1.0):
        H = self.L.H; hz = self.hz
        y = np.arange(0, H, 2, dtype=f32)[:, None] + 1
        el = np.clip((hz - y) / hz, 0, 1)
        zen = np.array([0.012, 0.075, 0.42], f32); hor = np.array([0.30, 0.50, 0.85], f32)
        k = np.exp(-el / 0.35)[..., None]
        sky = (zen * (1 - k) + hor * k) * np.ones((1, self.dx.shape[1], 1), f32)
        sky += (np.exp(-self.d / 45) * 0.9 + np.exp(-self.d / 200) * 0.06)[..., None] * np.array([1.0, 0.95, 0.85], f32)
        return sky * level

    def beams_layer(self, t, col_u=0.0):
        """giant chromatic beams; col_u 0..1 = collapse progress (spiral in, hot colours, shrinking reach)"""
        twist = 2.6 * ease(col_u) ** 1.3
        spin = 0.05 * t + 1.6 * col_u ** 2
        phi = self.phi + twist * np.log(self.d / 30.0)
        reach = 1500 * (1 - 0.78 * ease(col_u))
        rad = (1 - np.exp(-self.d / 35)) * (np.exp(-self.d / reach) * 0.9 + 0.12 * np.exp(-self.d / (reach * 2.2)))
        if col_u > 0:                                                     # inward-flowing streaks
            rad = rad * (1 + 0.8 * col_u * (np.sin(self.d / 22 + 38 * t) * 0.5 + 0.5) ** 2)
        acc = np.zeros(self.dx.shape + (3,), f32)
        for b in self.beams:
            a = b["a"] + spin * b["sp"]
            dp = (phi - a + np.pi) % (2 * np.pi) - np.pi
            w = b["w"] * (1 + 0.25 * math.sin(t * 0.9 * b["sp"] + b["ph"]))
            g = np.exp(-(dp / w) ** 2 * 1.6)
            I = b["I"] * (0.75 + 0.25 * math.sin(t * 1.3 * b["sp"] + b["ph"] * 2))
            if b["rainbow"]: c = palette((b["hue"] + dp / w * 0.32) % 1.0)
            else: c = palette(np.full(dp.shape, b["hue"], f32))
            if col_u > 0:
                hc = HOT[self.beams.index(b) % len(HOT)]
                c = c * (1 - ease(col_u)) + hc * ease(col_u)
            acc += c * (g * I)[..., None]
        return acc * rad[..., None] * 0.30

    def sun_core(self, img, t):
        """Sun core: normal -> swell/wobble -> implode -> point"""
        cx, cy = self.C
        if t < T_COL: R, I, wob = 16.0, 1.0, 0.0
        elif t < T_SWELL1:
            u = ease((t - T_COL) / (T_SWELL1 - T_COL)); R, I, wob = 16 + 58 * u, 1 + 0.6 * u, u
        elif t < T_IMPL:
            u = (t - T_SWELL1) / (T_IMPL - T_SWELL1); R, I, wob = max(74 * (1 - ease(u) ** 0.7), 2.0), 1.6 + 6 * u ** 2, 1 - u
        else: R, I, wob = 2.0, 8.0, 0.0
        def fn(d, dx, dy):
            ang = np.arctan2(dy, dx)
            rr = R * (1 + wob * (0.09 * np.sin(3 * ang + 9 * t) + 0.06 * np.sin(5 * ang - 13 * t) + 0.04 * np.sin(8 * ang + 21 * t)))
            core = smooth(rr + 1.5, rr - 1.5, d)
            hot = np.array([1.0, 0.92, 0.80], f32) * (1 - wob) + np.array([1.0, 0.62, 0.30], f32) * wob
            v = core[..., None] * hot * 30 * I + (np.exp(-np.maximum(d - rr, 0) / (rr * 0.6 + 6)) * 3.0 * I)[..., None] * np.array([1.0, 0.75, 0.45], f32)
            v += (np.exp(-d / (rr * 3 + 40)) * 0.8 * I)[..., None] * np.array([1.0, 0.8, 0.6], f32)
            return v
        splat(img, cx, cy, 520, fn)

    # -------------------------------------------------------------------------------------------- night + hole
    def sky_night(self, t, S):
        L = self.L; W, H = L.W, L.H; hz = self.hz
        y = np.arange(H, dtype=f32)[:, None]
        el = np.clip((hz - y) / hz, 0, 1)
        zen = np.array([0.006, 0.007, 0.045], f32); hor = np.array([0.020, 0.030, 0.13], f32)
        k = np.exp(-el / 0.30)[..., None]
        base = (zen * (1 - k) + hor * k) * np.ones((1, W, 1), f32)
        stars = self.stars.render(self.cam, t, cx=2020, cy=1180, rot=-8, gain=1.8, twinkle=1.0, plate_gain=0.9, air=0.6)
        sky = base + stars * np.array([0.85, 0.9, 1.1], f32)
        if S > 0: sky = self.lens_swirl(sky, t, S)
        return sky

    def lens_swirl(self, sky, t, S):
        """strong point-lens warp + slow differential swirl of the starfield around the hole"""
        cx, cy = self.C; Rs = self.Rs * S; thE = 1.55 * Rs
        Rp = int(min(7 * Rs + 60, 900))
        H, W = sky.shape[:2]
        x0, x1, y0, y1 = max(0, int(cx - Rp)), min(W, int(cx + Rp)), max(0, int(cy - Rp)), min(H, int(cy + Rp))
        yy, xx = self.yy[y0:y1, x0:x1], self.xx[y0:y1, x0:x1]
        tx, ty = xx + 0.5 - cx, yy + 0.5 - cy
        r2 = tx * tx + ty * ty + 1.0; r = np.sqrt(r2)
        k = 1 - thE ** 2 / r2
        fade = smooth(Rp, Rp * 0.65, r)
        k = k * fade + (1 - fade)
        bx, by = tx * k, ty * k
        ang = (0.10 * (t - T_BH0) + 0.6) * np.exp(-(r / (3.2 * Rs)) ** 2) * fade
        ca, sa = np.cos(ang), np.sin(ang)
        mx = (cx + bx * ca - by * sa - 0.5).astype(f32); my = (cy + bx * sa + by * ca - 0.5).astype(f32)
        out = sky.copy()
        out[y0:y1, x0:x1] = cv2.remap(sky, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return out

    def hole(self, img, t, S, pulse):
        """black core, photon ring, lensed disk (front band + upper/lower arches), infalling spiral gas, halo"""
        if S <= 0.02: return
        cx, cy = self.C; Rs = self.Rs * S
        Rb = int(min(6.5 * Rs + 40, 1000))
        H, W = img.shape[:2]
        x0, x1, y0, y1 = max(0, int(cx - Rb)), min(W, int(cx + Rb)), max(0, int(cy - Rb)), min(H, int(cy + Rb))
        dx = self.xx[y0:y1, x0:x1] + 0.5 - cx; dy = self.yy[y0:y1, x0:x1] + 0.5 - cy
        al = math.radians(-9); ca, sa = math.cos(al), math.sin(al)
        xr = dx * ca + dy * sa; yr = -dx * sa + dy * ca
        r = np.sqrt(dx * dx + dy * dy) + 1e-3
        th = np.arctan2(yr, xr)
        reg = img[y0:y1, x0:x1]
        # halo + infalling spiral gas (outside the shadow)
        sp = np.arctan2(yr / 0.62, xr)
        rr = np.sqrt(xr ** 2 + (yr / 0.62) ** 2) + 1e-3
        arms = (0.5 + 0.5 * np.cos(2 * (sp + 1.9 * np.log(rr / Rs)) - 0.9 * t)) ** 3
        arms2 = (0.5 + 0.5 * np.cos(3 * (sp + 1.4 * np.log(rr / Rs)) - 1.3 * t + 1.0)) ** 4
        gas = (arms * 0.8 + arms2 * 0.5) * np.exp(-(rr / (3.6 * Rs)) ** 1.6) * smooth(1.05 * Rs, 1.9 * Rs, rr)
        gcol = np.array([0.55, 0.25, 1.0], f32) * (1 - np.exp(-rr / (2.5 * Rs)))[..., None] + np.array([1.0, 0.45, 0.85], f32) * np.exp(-rr / (2.5 * Rs))[..., None]
        reg += gas[..., None] * gcol * 0.55 * pulse
        reg += (np.exp(-np.maximum(r - Rs, 0) / (0.9 * Rs)) * 0.55 + np.exp(-r / (3.5 * Rs)) * 0.10)[..., None] * np.array([0.75, 0.6, 1.0], f32) * pulse
        # disk texture lookup (Keplerian shear)
        def disk_val(rho, psi):
            om = 1.6 * (np.maximum(rho, 0.3 * Rs) / (1.3 * Rs)) ** -1.5
            u = ((psi - om * t) / (2 * np.pi) % 1.0) * 1024
            v = np.clip((rho / Rs - 1.2) / 2.4, 0, 1) * 255
            tex = cv2.remap(self.disk_tex, u.astype(f32), v.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
            prof = smooth(1.22 * Rs, 1.36 * Rs, rho) * np.exp(-(rho - 1.3 * Rs) / (0.85 * Rs)) * smooth(3.7 * Rs, 3.1 * Rs, rho)
            return prof * tex
        def disk_col(rho, xside):
            w = np.clip((rho / Rs - 1.25) / 2.2, 0, 1)[..., None]
            c = np.array([1.0, 0.97, 0.92], f32) * (1 - w) + np.array([1.0, 0.62, 0.30], f32) * w * 0.8 + np.array([0.9, 0.35, 1.0], f32) * w * 0.35
            dop = (1 - 0.55 * np.clip(xside, -1, 1)) ** 2.2                          # approaching (left) side brighter
            return c * dop[..., None]
        ci = 0.13
        rho_f = np.sqrt(xr ** 2 + (yr / ci) ** 2); psi_f = np.arctan2(yr / ci, xr)
        dv = disk_val(rho_f, psi_f)
        front = dv * (yr > 0)                                                        # near half: crosses in front of the core
        back = dv * (yr <= 0) * (r > Rs * 1.02)
        # lensed image of the far half: arch over the top (thick) and under the bottom (thin)
        up_w = 0.95 * Rs * np.abs(np.sin(th)) ** 0.55 + 0.05 * Rs
        lo_w = 0.32 * Rs * np.abs(np.sin(th)) ** 0.8 + 0.03 * Rs
        g_up = (yr < 0) * smooth(Rs * 1.0, Rs * 1.06, r) * smooth(Rs * 1.06 + up_w, Rs * 1.03 + up_w * 0.5, r)
        g_lo = (yr > 0) * smooth(Rs * 1.0, Rs * 1.04, r) * smooth(Rs * 1.04 + lo_w, Rs * 1.02 + lo_w * 0.4, r)
        rho_a = 1.3 * Rs + (r - Rs) / np.maximum(up_w, 1) * 2.0 * Rs
        arch_up = disk_val(rho_a, th * 1.0 + 3.0) * g_up * 1.25
        rho_l = 1.3 * Rs + (r - Rs) / np.maximum(lo_w, 1) * 1.6 * Rs
        arch_lo = disk_val(rho_l, -th + 1.0) * g_lo * 0.7
        # shadow: kill everything behind the core
        shadow = smooth(Rs * 0.995, Rs * 1.012, r)
        reg *= shadow[..., None]
        xs = xr / np.maximum(r, 1)
        reg += (back[..., None] * disk_col(rho_f, xs) + arch_up[..., None] * disk_col(rho_a, xs) + arch_lo[..., None] * disk_col(rho_l, xs)) * 5.0 * pulse
        ring = np.exp(-((r - Rs * 1.025) / (0.010 * Rs + 0.8)) ** 2) * 9.0 + np.exp(-np.maximum(r - Rs, 0) / (0.06 * Rs)) * (r > Rs) * 1.6
        reg += ring[..., None] * np.array([0.92, 0.85, 1.0], f32) * pulse
        reg += front[..., None] * disk_col(rho_f, xs) * 5.0 * pulse
        img[y0:y1, x0:x1] = reg

    # -------------------------------------------------------------------------------------------- cold
    def frost_wave(self, fgc, t, p, level):
        """blue-white frost front sweeping left -> right across grass and trees"""
        fg = self.fg; W, H = self.L.W, self.L.H
        field = self.xx / W * 0.85 + (1 - self.yy / H) * 0.25 + self.noise_x * 0.06
        front = p * 1.35 - 0.1
        m = smooth(0.0, 0.05, front - field) * np.maximum(fg.frost_cover, 0.25 * fg.a)
        edge = np.exp(-((front - field) / 0.018) ** 2) * fg.a
        y = lum(fgc)[..., None]
        tex = (fg.hf ** 1.4 * fg.crystal)[..., None]
        fcol = (y * 2.2 + 0.03 * level) * tex * np.array([0.72, 0.88, 1.15], f32)
        out = fgc * (1 - m[..., None]) + fcol * m[..., None]
        out += edge[..., None] * np.array([0.35, 0.65, 1.0], f32) * 0.25 * level
        g = fg.glint_xy; mg = m[g[:, 1], g[:, 0]]
        tw = np.clip(np.sin(t * fg.glint_fr * 6.283 + fg.glint_ph), 0, 1) ** 10
        val = mg * tw * fg.glint_sz * 2.5 * level
        sel = val > 1e-4
        if sel.any():
            lay = np.zeros((H, W), f32); np.add.at(lay, (g[sel, 1], g[sel, 0]), val[sel])
            lay = cv2.GaussianBlur(lay, (0, 0), 0.8) * 5 + cv2.GaussianBlur(lay, (0, 0), 3.0) * 3
            out += lay[..., None] * np.array([0.8, 0.92, 1.0], f32)
        return out

    def mist_layer(self, t, a):
        W, H = self.L.W, self.L.H; hz = self.hz
        mu = (self.xx[::2, ::2] * 0.45 + t * 18) % 1024; mv = (self.yy[::2, ::2] * 0.9 + 40 * np.sin(self.xx[::2, ::2] / 300 + t * 0.2)) % 512
        mn = cv2.remap(self.mist, mu.astype(f32), mv.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        band = smooth(hz - 160, hz + 30, self.yy[::2, ::2]) * (1 - 0.5 * smooth(hz + 200, H, self.yy[::2, ::2]))
        return self.up(np.clip(mn * 1.6 - 0.45, 0, 1) * band * a)

    # -------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        L = self.L; W, H = L.W, L.H; fg = self.fg; s = self.st(t)
        a = fg.a[..., None]
        if t < T_OUT:
            col_u = 0.0 if t < T_COL else min(1.0, (t - T_COL) / (T_IMPL - T_COL))
            sky = self.sky_day(t)
            bm = self.beams_layer(t, col_u)
            img = self.up(sky + bm * (1 - 0.4 * col_u))
            self.sun_core(img, t)
            tint = self.up(bm.mean(axis=(0, 1), keepdims=True) * np.ones_like(bm[..., :1]))
            fgc = fg.day(1.0) * (1 - 0.25 * col_u) + self.up(bm) * 0.06 + tint * 0.10
            img = img * (1 - a) + fgc * a
            if t > T_IMPL:                                                        # final white flash
                f = (t - T_IMPL) / (T_OUT - T_IMPL)
                img = img + (8.0 * f ** 2) * np.array([1.0, 0.97, 0.95], f32)
        else:
            S = ease((t - T_BH0) / (T_BH1 - T_BH0)) * (1 + 0.06 * math.sin(max(t - T_BH0, 0) * 3) * math.exp(-max(t - T_BH1, 0) / 1.5))
            pulse = 1 + 0.14 * math.sin(2 * math.pi * t / 1.7) + sum(1.3 * math.exp(-((t - tf) / 0.22) ** 2) for tf in FLARES)
            sky = self.sky_night(t, S)
            self.hole(sky, t, S, pulse)
            if t < T_BH1 + 0.5:                                                    # lingering ember where the Sun was
                e = math.exp(-(t - T_OUT) / 0.9)
                splat(sky, self.C[0], self.C[1], 400, lambda d, dx, dy: ((np.exp(-d / 6) * 20 + np.exp(-d / 60) * 1.5) * e)[..., None] * np.array([1.0, 0.6, 0.9], f32))
            fgc = self.fg_night.copy()
            fgc += fg.flat * (np.array([0.10, 0.06, 0.18], f32) * 0.15 * S * pulse)            # violet light from the hole
            p = ramp(t, T_COLD, T_YEAR + 1.2)
            if p > 0: fgc = self.frost_wave(fgc, t, p, 0.5)
            fgc = fg.lamps_light(fgc, s["lamps"] * 3.0, t)
            img = sky * (1 - a) + fgc * a
            if p > 0:
                mi = self.mist_layer(t, 0.35 * p)
                img = img * (1 - mi[..., None] * 0.5) + mi[..., None] * np.array([0.10, 0.14, 0.26], f32)
            # impact: shockwave ring + white-out decaying, sky crash
            u = t - T_OUT
            if u < 1.4:
                R = 2300 * (u / 1.4) ** 0.6; wdt = 18 + 60 * u
                dd = np.sqrt((self.xx - self.C[0]) ** 2 + (self.yy - self.C[1]) ** 2)
                for ch, off in ((0, 8), (1, 0), (2, -8)):
                    img[..., ch] += np.exp(-((dd - R - off) / wdt) ** 2) * 2.5 * math.exp(-u / 0.6)
                img += 9.0 * math.exp(-u / 0.16) * np.array([1.0, 0.96, 0.98], f32)
            if t > T_WHITE:                                                        # final flare -> white-out
                v = ease((t - T_WHITE) / (DUR - 0.25 - T_WHITE))
                dd = np.sqrt((self.xx - self.C[0]) ** 2 + (self.yy - self.C[1]) ** 2)
                R = 60 + 2600 * v ** 1.5
                glow = np.exp(-np.maximum(dd - R, 0) / (120 + 600 * v)) * (2 + 30 * v)
                img += glow[..., None] * np.array([1.0, 0.86, 0.95], f32)
                img += (40 * v ** 3) * np.array([1.0, 0.9, 0.95], f32)
        img = bloom(img, 0.8 if t < T_IMPL else 1.4)
        out = tonemap(img, 1.0)
        out = self.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.18)
        self.overlay(out, t, s)
        return out

    def chroma(self, out):
        """lateral chromatic aberration (subtle, stronger toward the corners)"""
        W, H = self.L.W, self.L.H
        o = out.copy()
        for ch, k in ((0, 1.0016), (2, 0.9984)):
            M = np.float32([[k, 0, (1 - k) * W / 2], [0, k, (1 - k) * H / 2]])
            o[..., ch] = cv2.warpAffine(out[..., ch], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return o

    def overlay(self, out, t, s):
        L = self.L; W = L.W
        L.cap_y = 1010 if L.vertical else 600
        big = int(L.hud_size * 1.6)
        ry = 1330 if L.vertical else 860
        if T_NOW - 0.1 < t < T_OUT + 0.8:
            u = min(max((t - T_NOW) / (T_OUT - T_NOW), 0.0), 1.0)
            sec = 500 * (u ** 1.6) if t < T_OUT else 500
            a = ramp(t, T_NOW - 0.1, T_NOW + 0.2) * (1 - ramp(t, T_OUT + 0.4, T_OUT + 0.8))
            hud_text(out, "SUNLIGHT STILL ON ITS WAY" if t < T_OUT else "LAST LIGHT ARRIVES", W / 2, ry - big * 0.95, int(L.hud_size * 0.42), "Bold", (240, 244, 250), a, 0.22)
            hud_text(out, f"T + {int(sec) // 60}:{int(sec) % 60:02d}", W / 2, ry, big, "Black", (255, 255, 255) if t < T_OUT else (255, 150, 70), a, 0.03, display=True)
        if t > T_COLD - 0.2 and t < T_WHITE + 0.3:
            a = ramp(t, T_COLD - 0.2, T_COLD + 0.2) * (1 - ramp(t, T_WHITE, T_WHITE + 0.3))
            d = day_of(t); tc = temp_c(d)
            sign = "−" if tc < -0.5 else "+"
            hud_text(out, f"EARTH · DAY {int(d)}", W / 2, ry - big * 0.95, int(L.hud_size * 0.42), "Bold", (220, 235, 255), a, 0.22)
            hud_text(out, f"{sign}{abs(round(tc)):d}°C", W / 2, ry, int(big * 1.25), "Black", (200, 232, 255), a, 0.02, display=True)
        fy = 1240 if L.vertical else 760
        fs = int(L.hud_size * 0.62)
        o0, o1 = LN["orbit"]["start"], LN["bh"]["start"]
        b0, b1 = LN["bh"]["start"], LN["scope"]["start"]
        s0, s1 = LN["scope"]["start"], LN["cold"]["start"]
        for txt, a0, a1, col in (("SAME MASS · SAME ORBIT", o0, o1, (200, 225, 255)), ("EVENT HORIZON ≈ 6 KM", b0, b1, (255, 210, 160)),
                                 ("EINSTEIN RING ≈ 1.4′", s0, s1 - 0.3, (230, 205, 255))):
            al = ramp(t, a0, a0 + 0.25) * (1 - ramp(t, a1 - 0.2, a1 + 0.05))
            if al > 0.01: hud_text(out, txt, W / 2, fy, fs, "Black", col, al, 0.10, display=True)
        self.caps.draw(out, t)


def run(vertical, stills=None):
    sc = VFX(vertical); tag = "vfx_vert" if vertical else "vfx_wide"
    if stills:
        os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
        for t in stills:
            t0 = time.time(); im = sc.frame(t)
            Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(SCR, "stills", f"{tag}_{t:05.2f}.png"))
            print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)
        return
    n = int(round(DUR * FPS))
    enc = Encoder(os.path.join(SCR, f"video_{tag}.mp4"), sc.L.W, sc.L.H, FPS, crf=16)
    t0 = time.time()
    for i in range(n):
        enc.write(sc.frame(i / FPS))
        if i % 60 == 0: print(f"{tag} frame {i}/{n}  {time.time() - t0:.0f}s", flush=True)
    enc.close(); print("done", time.time() - t0)


if __name__ == "__main__":
    vert = sys.argv[1] != "wide"
    st = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    run(vert, st)
