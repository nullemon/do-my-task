"""WHAT IF GALAXIES WERE BRIGHT ENOUGH TO SEE? -- one locked tripod shot of the city (C_city) at night, VFX spectacle.
Every galaxy is shown at its TRUE angular size (gnomonic lens, f = F_PX = 6000 px per radian = 104.7 px per degree:
a telephoto view, 18.2 deg tall). Only the surface brightness is raised to long-exposure-camera level.
The star field is the real HYG v4.1 sky (V < 7) around Andromeda, which sits at its real place; the frame is rolled
103 deg (one moment of the night) so Andromeda's disc runs across the sky.
  night (eye view: a faint smudge; six full Moons laid along it) -> Andromeda + M32 + M110 (3.2 deg, 6x the Moon) ->
  Triangulum (1.2 deg) -> Large + Small Magellanic Clouds (10.8 deg / 5.3 deg) -> Whirlpool (11', tiny + loupe) ->
  ALL at once + the Milky Way's core -> white-out -> plain city night (loops)
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py vert                  full render -> SCR/video_vert.mp4
  /home/user/ttsenv/bin/python short.py vert 1.0,9.5          stills -> SCR/stills/vert_<t>.png
  /home/user/ttsenv/bin/python short.py info
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (pylib path)
import numpy as np, cv2
from PIL import Image
from lib.core import f32, Layout, ramp, smooth, ease, splat, lum, fbm2, bbcolor
from lib.foreground import Foreground
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish, Encoder
from lib.audio import place
from skygeo import eq_vec, EQ2GAL
from mwsky import canvas, WL, PXD as CPXD, HB

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B2-galaxies-visible"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/C_city.png"
FPS = 30
LEAD, TAIL = 0.25, 1.30
F_PX = 6000.0; PXD = F_PX * math.pi / 180; SS = 2.0
M31 = (10.68471, 41.26875)
ROLL = math.radians(103.0)
P31 = (540.0, 700.0)
MOON_PX = 0.52 * PXD

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]


# ------------------------------------------------------------------------------------------------ scenes
# items: (sprite key, x, y, extra rotation deg); tc: title colour; lc: light cast on the city (linear RGB)
SC = {
    "night": dict(items=[], I=0.0, beams=[(0.3, 0.5, 1.0)], bI=0.0, expo=1.15, c=P31),
    "m31": dict(items=[("m31", *P31, 0)], name="ANDROMEDA (M31)", tc=(170, 205, 255),
                l=["6× THE MOON'S SIZE", "2.5 MILLION LY", "1 TRILLION STARS"], I=0.6, gain=3.0,
                beams=[(0.45, 0.65, 1.0), (1.0, 0.8, 0.45), (0.75, 0.5, 1.0), (0.35, 0.95, 1.0)], bI=0.30, expo=1.05, c=P31,
                moon=(880, 830), halo=(0.55, 0.65, 1.0)),
    "m33": dict(items=[("m33", 540.0, 720.0, 0)], name="TRIANGULUM (M33)", tc=(160, 235, 255),
                l=["2.3× THE MOON'S SIZE", "2.7 MILLION LY", "~40 BILLION STARS"], I=0.45, gain=3.4,
                beams=[(0.3, 0.85, 1.0), (0.6, 0.6, 1.0), (1.0, 0.95, 0.8)], bI=0.26, expo=1.08, c=(540.0, 720.0),
                moon=(790, 830), halo=(0.45, 0.75, 1.0)),
    "mc": dict(items=[("lmc", 470.0, 920.0, 0), ("smc", 800.0, 600.0, 0)], name="MAGELLANIC CLOUDS", tc=(255, 150, 210),
               l=["LMC 20× · SMC 10× THE MOON'S SIZE", "160,000 & 200,000 LY", "LMC: ~30 BILLION STARS"], I=0.8, gain=3.6,
               beams=[(1.0, 0.35, 0.65), (0.45, 0.7, 1.0), (1.0, 0.85, 0.7), (0.7, 0.4, 1.0)], bI=0.34, expo=1.0, c=(470.0, 920.0),
               moon=(985, 1150), halo=(0.75, 0.6, 1.0)),
    "m51": dict(items=[("m51", 720.0, 540.0, 0)], name="WHIRLPOOL (M51)", tc=(255, 140, 230),
                l=["1/3 OF THE MOON'S SIZE", "~30 MILLION LY", "~100 BILLION STARS"], I=0.3, gain=3.8,
                beams=[(0.8, 0.35, 1.0), (0.3, 0.6, 1.0), (1.0, 0.45, 0.6)], bI=0.22, expo=1.1, c=(720.0, 540.0),
                moon=(880, 560), halo=(0.8, 0.45, 1.0), loupe=(420.0, 770.0, 215.0)),
    "all": dict(items=[("core", 640.0, 1230.0, -103 - 22), ("lmc", 300.0, 900.0, 0), ("smc", 850.0, 800.0, 0), ("m33", 930.0, 520.0, 0),
                       ("m31", 600.0, 330.0, 0)],
                I=0.65, gain=3.6, beams=[(1.0, 0.6, 0.25), (0.4, 0.7, 1.0), (1.0, 0.4, 0.7), (0.5, 1.0, 0.8)], bI=0.38, expo=1.0,
                c=(560.0, 760.0),
                labels=[("ANDROMEDA", 600, 225), ("TRIANGULUM", 930, 440), ("SMC", 850, 650), ("LMC", 150, 560), ("MILKY WAY CORE", 820, 1120)]),
}
GAIN = dict(m31=1.0, m33=1.0, lmc=1.0, smc=1.0, m51=1.0, core=0.55)

# ------------------------------------------------------------------------------------------------ timeline
T_MOONS = wt("hook", "6×") - 0.05
T_MOONS1 = wt("hook2", "YOU")
T_CAN = wt("m31a", "BUT")
T_SW = dict(m31=wt("m31", "ANDROMEDA") - 0.12, m33=LN["m33"]["start"] - 0.06, mc=LN["mc"]["start"] - 0.06,
            m51=LN["m51"]["start"] - 0.06, all=LN["end"]["start"] - 0.06)
T_BACK = wt("end3", "YOUR") - 0.08                       # white-out peak -> plain city night
T_WO0 = T_BACK - 0.75
T_BIG = wt("end", "BIG")
COLLAPSE, BLOOM = 0.42, 0.65
SWAPS = [(T_SW[k], k) for k in ("m31", "m33", "mc", "m51", "all")] + [(T_BACK, "night")]
PULSES = [wt("m31", "TRILLION"), wt("m33", "SPIRAL"), wt("m33", "THREE"), wt("mc", "20"), wt("mc", "MOONS"), wt("m51", "TINY"),
          wt("m51", "THIRD"), T_BIG]


def scene_at(t):
    cur, t0, prev = "night", -10.0, "night"
    for i, (ts, k) in enumerate(SWAPS):
        if t >= ts: cur, t0, prev = k, ts, (SWAPS[i - 1][1] if i > 0 else "night")
    nxt = [ts for ts, k in SWAPS if ts > t]
    return cur, prev, t0, (nxt[0] if nxt else 1e9)


def back_out(u, s=2.0):
    u = min(max(u, 0.0), 1.0) - 1; return 1 + u * u * ((s + 1) * u + s)


def lerp(a, b, w): return a + (b - a) * w


def pal_list(cols, x):
    C = np.array(cols + [cols[0]], f32); n = len(cols)
    p = (x % 1.0) * n; i = np.floor(p).astype(np.int32); fr = (p - i)[..., None]
    return C[i] * (1 - fr) + C[i + 1] * fr


def rot2(a): c, s = math.cos(a), math.sin(a); return np.array([[c, -s], [s, c]])


# ------------------------------------------------------------------------------------------------ scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(True); W, H = L.W, L.H
        self.fg = fg = Foreground(FG_PATH, L, lamps=[], hz_frac=0.97)
        self.hz = float(fg.horizon)
        L.cap_y = 1010
        yy, xx = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xx, yy
        # ---- night sky: deep blue -> violet, warm city light dome at the horizon (never black)
        e = np.clip((self.hz - yy) / self.hz, 0, 1)
        k = np.exp(-e / 0.30)[..., None]
        zen = np.array([0.010, 0.011, 0.075], f32); hor = np.array([0.040, 0.044, 0.180], f32)
        night = zen * (1 - k) + hor * k
        night += np.exp(-((e - 0.45) / 0.22) ** 2)[..., None] * np.array([0.020, 0.004, 0.036], f32)
        night += np.exp(-e / 0.12)[..., None] * np.array([0.070, 0.034, 0.036], f32)
        n = cv2.resize(fbm2((96, 96), 61, 3.0), (W, H), interpolation=cv2.INTER_CUBIC)
        self.night = (night * (1 + 0.06 * n)[..., None]).astype(f32)
        # ---- the real sky around Andromeda (gnomonic, tangent at M31, rolled)
        d0 = eq_vec(*M31); a0 = math.radians(M31[0])
        east = np.array([-math.sin(a0), math.cos(a0), 0.0]); north = np.cross(d0, east)
        R = rot2(ROLL)
        z = np.load(os.path.join(SCR, "stars.npz"))
        v = eq_vec(z["ra"], z["dec"]); c = v @ d0
        E = (v @ east) / np.maximum(c, 1e-3); N = (v @ north) / np.maximum(c, 1e-3)
        s0 = np.stack([-E * F_PX, -N * F_PX], 1) @ R.T
        sx, sy = s0[:, 0] + P31[0], s0[:, 1] + P31[1]
        sel = (c > 0.5) & (sx > -5) & (sx < W + 5) & (sy > -5) & (sy < H + 5)
        self.sx, self.sy, mag = sx[sel].astype(f32), sy[sel].astype(f32), z["mag"][sel]
        self.sflux = (3.6 * 10 ** (-0.4 * 0.80 * mag)).astype(f32)
        bv = np.clip(z["ci"][sel], -0.4, 2.0); T = 4600 * (1 / (0.92 * bv + 1.7) + 1 / (0.92 * bv + 0.62))
        cols = np.stack([bbcolor(x) for x in np.clip(T, 2600, 30000)]); yv = cols @ np.array([0.2126, 0.7152, 0.0722])
        cols = np.clip(yv[:, None] + (cols - yv[:, None]) * 1.6, 0.02, None); cols /= (cols @ np.array([0.2126, 0.7152, 0.0722]))[:, None]
        self.scol = cols.astype(f32)
        self.sph = np.random.default_rng(3).uniform(0, 100, len(mag)).astype(f32)
        self.glint = np.where(mag < 3.0)[0]
        print("stars in frame", len(mag), "brightest", float(mag.min()) if len(mag) else None)
        # Milky Way glow on the same projection (static: locked camera)
        mw = canvas(os.path.join(SCR, "mw_gal.npz"))
        s = np.stack([xx - P31[0], yy - P31[1]], -1) @ R          # = R^T applied to row vectors
        Eo = -s[..., 0] / F_PX; No = -s[..., 1] / F_PX
        rays = d0[None, None] + Eo[..., None] * east[None, None] + No[..., None] * north[None, None]
        rays /= np.linalg.norm(rays, axis=-1, keepdims=True)
        g = rays @ EQ2GAL.T
        l = np.arctan2(g[..., 1], g[..., 0]); b = np.arcsin(np.clip(g[..., 2], -1, 1))
        mx = (WL / 2 + np.degrees(l) * CPXD) % WL; my = HB / 2 - np.degrees(b) * CPXD
        self.mw = cv2.remap(mw, mx.astype(f32), my.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP) * 1.6
        # ---- sprites
        sp = np.load(os.path.join(SCR, "sprites.npz"))
        self.sp = {}
        for kk in ("m31", "m33", "lmc", "smc", "m51", "m51L", "core", "moon"):
            im = sp[kk].astype(f32); h, w = im.shape[:2]
            sig = max(1.5, 0.02 * max(h, w)); lo = cv2.GaussianBlur(im, (0, 0), sig)
            light = sp[kk + "_light"]; light = light / max(float(light.max()), 1e-6)
            ss = 1.0 if kk in ("core", "m51L") else SS
            self.sp[kk] = dict(img=im, lo=lo, hi=im - lo, c=sp[kk + "_c"], light=light.astype(f32), w=w, h=h, ss=ss)
        self.shim = fbm2((256, 256), 81, 2.0)
        r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 9 + r.uniform(-0.2, 0.2), w=r.uniform(0.10, 0.20), I=r.uniform(0.7, 1.2), hue=r.uniform(0, 1),
                           ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(9)]
        hw, hh = W // 2, H // 2
        hy, hx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.hx, self.hy = hx, hy
        # loupe backdrop stars
        rr = np.random.default_rng(9); ls = np.zeros((600, 600, 3), f32)
        for _ in range(260):
            x, y = rr.uniform(0, 600, 2); ls[int(y), int(x)] += rr.uniform(0.02, 0.4) * (0.6 + 0.4 * rr.uniform(0, 1, 3))
        self.loupe_stars = cv2.GaussianBlur(ls, (0, 0), 0.7) * 1.5
        # ---- city: night grade with its own lights; relit by the galaxy light
        a = fg.a; self.a = a[..., None]
        rgb = fg.rgb; f = fg.flat; y = lum(f)[..., None]
        mxc = rgb.max(2); warm = rgb[..., 0] - rgb[..., 2]
        win = (smooth(0.10, 0.42, mxc) * smooth(0.0, 0.08, warm)).astype(f32)
        self.lights = (rgb * win[..., None] * 2.6 + win[..., None] * np.array([0.20, 0.10, 0.03], f32)).astype(f32)
        self.base = ((f * 0.35 + y * 0.65) * np.array([0.30, 0.36, 0.75], f32) * 0.30 * (1 - win[..., None])).astype(f32)
        self.alb = np.clip(f * (1 - 0.7 * win[..., None]), 0, 1).astype(f32)
        sk = np.clip((self.hz + 200 - yy) / (self.hz + 200 - fg.skyline.min()), 0, 1)
        self.skyfac = (0.35 + 0.65 * sk)[..., None].astype(f32)
        sh = np.zeros_like(a); sh[8:] = a[:-8]
        self.rim = (cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 2.5) * a)[..., None].astype(f32)
        emph = {"6×", "MOON", "ANDROMEDA", "TRILLION", "2.5", "TRIANGULUM", "THREE", "MAGELLANIC", "20", "TARANTULA", "PINK",
                "WHIRLPOOL", "TINY", "THIRD", "30", "BIG", "THIN", "SENSITIVE", "CAN'T"}
        self.caps = Captions(L, WORDS, emphasis=emph)

    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    # -------------------------------------------------------------------------------------------- stars
    def stars(self, t, dim):
        W, H = self.L.W, self.L.H
        acc = np.zeros((H + 2, W + 2, 3), f32)
        tw = np.exp(0.35 * (np.sin(t * 11.3 + self.sph) * 0.5 + np.sin(t * 19.7 + self.sph * 1.7) * 0.3 + np.sin(t * 31.1 + self.sph * 2.3) * 0.2) - 0.06)
        val = (self.sflux * tw * dim)[:, None] * self.scol
        x0 = np.floor(self.sx).astype(int); y0 = np.floor(self.sy).astype(int)
        fx = (self.sx - x0)[:, None]; fy = (self.sy - y0)[:, None]
        for oy, ox, wg in ((0, 0, (1 - fx) * (1 - fy)), (0, 1, fx * (1 - fy)), (1, 0, (1 - fx) * fy), (1, 1, fx * fy)):
            np.add.at(acc, (np.clip(y0 + oy, 0, H + 1), np.clip(x0 + ox, 0, W + 1)), val * wg)
        acc = acc[:H, :W]
        for i in self.glint:
            g = self.sflux[i] * 0.05 * dim * (1 + 0.35 * math.sin(t * 5 + self.sph[i])); c = self.scol[i] * 0.6 + 0.4
            splat(acc, self.sx[i], self.sy[i], 40, lambda d, dx, dy: ((np.exp(-np.abs(dy) / 0.8) * np.exp(-np.abs(dx) / 12) + np.exp(-np.abs(dx) / 0.8) * np.exp(-np.abs(dy) / 12)) * g)[..., None] * c)
        st = cv2.GaussianBlur(acc, (0, 0), 0.75) * 2.2
        big = acc * (acc.max(2, keepdims=True) > 0.3)
        return st + cv2.GaussianBlur(big, (0, 0), 2.5) * 2.0

    # -------------------------------------------------------------------------------------------- sprites
    def matrix(self, key, x, y, s, rot, ox=0.0, oy=0.0):
        S = self.sp[key]; k = s / S["ss"]
        A = rot2(ROLL + rot) * k
        cx, cy = S["c"]
        return np.float32([[A[0, 0], A[0, 1], x + ox - (A[0, 0] * cx + A[0, 1] * cy)],
                           [A[1, 0], A[1, 1], y + oy - (A[1, 0] * cx + A[1, 1] * cy)]])

    def sprite(self, out, key, x, y, t, s, rot, gain, shimmer=True):
        W, H = self.L.W, self.L.H; S = self.sp[key]
        if s < 1e-3 or gain <= 0: return
        px, py = 3 * math.sin(0.33 * t + len(key)), 2.5 * math.cos(0.27 * t + len(key))
        eff = s / S["ss"]; acc = np.zeros((H, W, 3), f32)
        for lay, sgn in ((S["lo"], 1.0), (S["hi"], -1.0)):
            src = lay; M = self.matrix(key, x, y, s, rot, px * sgn, py * sgn)
            if eff < 0.6:
                kk = max(eff / 0.8, 2.0 / max(S["w"], S["h"]))
                nw, nh = max(2, int(S["w"] * kk)), max(2, int(S["h"] * kk))
                src = cv2.resize(lay, (nw, nh), interpolation=cv2.INTER_AREA)
                M = M.copy(); M[:, 0] *= S["w"] / nw; M[:, 1] *= S["h"] / nh
            acc += cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        if shimmer and key in ("lmc", "smc", "core") and eff > 0.3:
            u = (self.xx * 0.10 + t * 6) % 256; v = (self.yy * 0.10 - t * 4) % 256
            n = cv2.remap(self.shim, u.astype(f32), v.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
            acc = cv2.remap(acc, self.xx + n * 1.3, self.yy + n * 0.9, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        out += np.maximum(acc, 0) * gain

    def moon(self, out, x, y, a):
        if a <= 0.01: return
        S = self.sp["moon"]; M = self.matrix("moon", x, y, 1.0, -ROLL + 0.0)
        out += cv2.warpAffine(S["img"], M, (self.L.W, self.L.H), flags=cv2.INTER_LINEAR) * a * 1.4
        splat(out, x, y, 70, lambda d, dx, dy: (np.exp(-np.maximum(d - MOON_PX / 2, 0) / 14) * 0.10 * a)[..., None] * np.array([0.9, 0.92, 1.0], f32))

    # -------------------------------------------------------------------------------------------- light rays
    def rays(self, t, P, Q, w, cx, cy, R, col_u, I):
        if I <= 0.005: return np.zeros(self.hx.shape + (3,), f32)
        dx, dy = self.hx - cx, self.hy - cy
        d = np.sqrt(dx * dx + dy * dy) + 1e-3; phi = np.arctan2(dy, dx) + 2.2 * ease(col_u) * np.log(d / 30.0)
        spin = 0.05 * t + 1.6 * col_u ** 2
        dd = np.maximum(d - R * 0.35, 0)
        rad = (1 - np.exp(-(dd + 4) / 60)) * np.exp(-dd / (700 + 0.6 * R))
        acc = np.zeros(d.shape + (3,), f32)
        for b in self.beams:
            a = b["a"] + spin * b["sp"]
            dp = (phi - a + np.pi) % (2 * np.pi) - np.pi
            wd = 0.6 * b["w"] * (1 + 0.3 * math.sin(t * 0.8 * b["sp"] + b["ph"]))
            gg = np.exp(-(dp / wd) ** 2 * 1.6) * b["I"] * (0.7 + 0.3 * math.sin(t * 1.2 * b["sp"] + 2 * b["ph"]))
            x = (b["hue"] + dp / wd * 0.25) % 1.0
            c = pal_list(P["beams"], x) * (1 - w) + pal_list(Q["beams"], x) * w if w < 1 else pal_list(Q["beams"], x)
            acc += c * gg[..., None]
        return acc * (rad * I * 0.30)[..., None]

    # -------------------------------------------------------------------------------------------- state
    def state(self, key, t, t0, t1):
        """-> scale, rotation, intensity multiplier, collapse progress"""
        if key == "night": return 1.0, 0.0, 1.0, 0.0
        u_in = (t - t0) / BLOOM
        s = back_out(u_in, 2.2); I = 0.4 + 0.6 * min(max(u_in * 3, 0), 1)
        if key == "all": s = 0.6 + 0.4 * back_out(u_in, 1.6)
        s *= 1 + 0.010 * math.sin(t * 0.9)
        rot = math.radians(0.5) * math.sin(0.21 * t + len(key))
        col_u = 0.0 if (t1 > 1e8 or SWAPS[-1][0] == t1) else max(0.0, 1 - (t1 - t) / COLLAPSE)
        if col_u > 0:
            if col_u < 0.45: s *= 1 + 0.22 * ease(col_u / 0.45)
            else: v = (col_u - 0.45) / 0.55; s *= 1.22 * (1 - ease(v) ** 0.7) + 0.01
            rot += 1.8 * col_u ** 2; I *= 1 + 2.5 * col_u ** 2
        return s, rot, I, col_u

    def light_of(self, key):
        Q = SC[key]
        if not Q["items"]: return np.array([0.5, 0.6, 1.0], f32)
        c = sum(self.sp[it[0]]["light"] * (0.3 if it[0] == "core" else 1.0) for it in Q["items"])
        c = c / max(float(c.max()), 1e-6)
        return (0.35 + 0.65 * c).astype(f32) * np.array(Q.get("halo", (1, 1, 1)), f32) ** 0.5

    # -------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        L = self.L; W, H = L.W, L.H
        cur, prev, t0, t1 = scene_at(t)
        P, Q = SC[prev], SC[cur]
        w = ramp(t, t0 - 0.12, t0 + 0.5) if t0 > 0 else 1.0
        s, rot, I, col_u = self.state(cur, t, t0, t1)
        pulse = 1 + 0.06 * math.sin(2 * math.pi * t / 1.7) + sum(0.35 * math.exp(-((t - tp) / 0.22) ** 2) for tp in PULSES)
        # ---- sky
        lvl = Q["I"] * w + P["I"] * (1 - w)
        sky = self.night + self.mw * (1 - 0.4 * lvl) + self.stars(t, 1.0 - 0.3 * lvl)
        gal = np.zeros((H, W, 3), f32)
        cx, cy = Q["c"]
        R = 120.0
        for key, x, y, r_ in Q["items"]:
            fade = 1.0
            if cur == "all":                                       # the finale builds up one by one, very fast
                i = [it[0] for it in Q["items"]].index(key); fade = ramp(t, t0 + 0.08 * i, t0 + 0.08 * i + 0.35)
            self.sprite(gal, key, x, y, t, s, rot + math.radians(r_), Q["gain"] * GAIN[key] * I * pulse * fade)
            R = max(R, 0.5 * max(self.sp[key]["w"], self.sp[key]["h"]) / self.sp[key]["ss"] * s * (0.5 if key == "core" else 1))
        if cur == "night":
            # what the eye gets: Andromeda's core as a faint grey smudge; six full Moons along its true length
            gal += np.zeros(3, f32)
            splat(gal, P31[0], P31[1], 40, lambda d, dx, dy: (np.exp(-d / 3.5) * 0.10 + np.exp(-d / 10) * 0.025)[..., None] * np.array([0.85, 0.88, 1.0], f32))
            if T_MOONS - 0.1 < t < T_CAN + 0.6:
                ax = rot2(ROLL) @ np.array([-math.sin(math.radians(35)), -math.cos(math.radians(35))])
                fo = 1 - ramp(t, T_MOONS1 + 0.2, T_MOONS1 + 0.7)
                for i in range(6):
                    off = (i - 2.5) * MOON_PX
                    a = ramp(t, T_MOONS + 0.12 * i, T_MOONS + 0.12 * i + 0.15) * fo
                    self.moon(gal, P31[0] + ax[0] * off, P31[1] + ax[1] * off, a)
            if T_CAN < t < T_SW["m31"]:                            # "what if your eyes could": the spot charges up
                u = ramp(t, T_CAN, T_SW["m31"])
                splat(gal, P31[0], P31[1], 300, lambda d, dx, dy: (np.exp(-d / (6 + 40 * u)) * 0.6 * u ** 2)[..., None] * np.array([0.6, 0.75, 1.0], f32))
        # moon for scale
        if Q.get("moon") and cur != "night":
            am = ramp(t, t0 + 0.45, t0 + 0.8) * (1 - ramp(t, t1 - 0.45, t1 - 0.2)) * (1 - ramp(t, T_WO0, T_WO0 + 0.3))
            self.moon(gal, *Q["moon"], am)
        # glow + light rays (half res)
        dx, dy = self.hx - cx, self.hy - cy; d = np.sqrt(dx * dx + dy * dy)
        lc = self.light_of(cur)
        lay = 0.0
        if cur != "night":
            aure = (np.exp(-np.maximum(d - R * 0.3, 0) / (160 + 0.5 * R)) * 0.14 + 0.006) * I * Q["I"]
            lay = aure[..., None] * lc + self.rays(t, P, Q, w, cx, cy, R, col_u, Q["bI"] * (1 + 1.2 * col_u) * min(1.0, I))
        if prev != "night" and w < 1:
            lay = lay + (0.03 * P["I"] * (1 - w)) * self.light_of(prev)
        if not isinstance(lay, float): gal = gal + self.up(lay * pulse)
        sky = sky + gal
        # ---- city: night grade, windows on, relit by the galaxy light
        lw = (Q["I"] * w * min(I, 1.6) + P["I"] * (1 - w)) * (0.9 + 0.1 * pulse)
        lcol = lc * w + self.light_of(prev) * (1 - w)
        fgc = self.base + self.alb * self.skyfac * lcol * lw * 0.9 + self.rim * lcol * (0.4 + 1.6 * lw) * 0.6
        fgc = fgc + self.lights * (1 + 0.04 * math.sin(t * 3.1))
        img = sky * (1 - self.a) + fgc * self.a
        # ---- M51 loupe (drawn over the city: it is an inset)
        if cur == "m51":
            la = ramp(t, t0 + 0.5, t0 + 0.85) * (1 - ramp(t, t1 - 0.45, t1 - 0.2))
            self.loupe(img, t, la, Q)
        # ---- swap flash + chromatic shockwave
        for ts, k in SWAPS:
            u = t - ts
            if -0.05 < u < 1.4:
                fc = 0.45 + 0.55 * self.light_of(k) if k != "night" else np.array([1.0, 0.95, 0.9], f32)
                img += (2.0 * math.exp(-max(u, 0) / 0.09) * ease((u + 0.05) / 0.05)) * fc
                if k == "night": continue
                pc = SC[k]["c"]
                Rr = 2400 * (max(u, 0) / 1.4) ** 0.6; wdt = 18 + 60 * u
                dd = np.sqrt((self.hx - pc[0]) ** 2 + (self.hy - pc[1]) ** 2)
                ring = np.zeros(dd.shape + (3,), f32)
                for ch, off in ((0, 12), (1, 0), (2, -12)):
                    ring[..., ch] = np.exp(-((dd - Rr - off) / wdt) ** 2) * 2.0 * math.exp(-max(u, 0) / 0.55)
                img += self.up(ring)
        if T_WO0 < t < T_BACK:
            v = ease((t - T_WO0) / (T_BACK - T_WO0)); img = img + (24 * v ** 2.5) * np.array([1.0, 0.94, 0.88], f32)
        img = self.chroma_bloom(img)
        out = tonemap(img, lerp(P["expo"], Q["expo"], w))
        y_ = out.mean(2, keepdims=True); out = np.clip(y_ + (out - y_) * 1.25, 0, 1)
        out = self.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.14)
        self.overlay(out, t, cur, t0, t1)
        return out

    def loupe(self, img, t, alpha, Q):
        if alpha <= 0.01: return
        cx, cy, R0 = Q["loupe"]; R = R0 * (0.55 + 0.45 * back_out(alpha, 1.6))
        H, W = img.shape[:2]
        r = int(R) + 8; x0, y0 = int(cx) - r, int(cy) - r
        g = np.arange(2 * r) + 0.5 - r
        XX, YY = np.meshgrid(g, g); rr = np.hypot(XX, YY)
        inside = smooth(R + 0.8, R - 0.8, rr)[..., None]
        base = np.array([0.006, 0.008, 0.035], f32) + (np.exp(-rr / R * 1.6) * 0.05)[..., None] * np.array([0.6, 0.35, 0.9], f32)
        patch = base + self.loupe_stars[:2 * r, :2 * r]
        S = self.sp["m51L"]; kz = R / R0
        A = rot2(ROLL + math.radians(1.5) * math.sin(t * 0.4)) * kz * (1 + 0.02 * math.sin(t * 0.7))
        M = np.float32([[A[0, 0], A[0, 1], r - (A[0, 0] * S["c"][0] + A[0, 1] * S["c"][1])], [A[1, 0], A[1, 1], r - (A[1, 0] * S["c"][0] + A[1, 1] * S["c"][1])]])
        patch = patch + cv2.warpAffine(S["img"], M, (2 * r, 2 * r), flags=cv2.INTER_LINEAR) * 1.9
        ring = np.exp(-((rr - R) / 2.4) ** 2)[..., None] * np.array([1.7, 1.55, 1.8], f32) + (np.exp(-np.maximum(rr - R, 0) / 14) * (rr > R) * 0.22)[..., None] * np.array([1.0, 0.7, 1.0], f32)
        ya, yb, xa, xb = max(0, y0), min(H, y0 + 2 * r), max(0, x0), min(W, x0 + 2 * r)
        sl = (slice(ya - y0, yb - y0), slice(xa - x0, xb - x0))
        reg = img[ya:yb, xa:xb]
        reg[:] = reg * (1 - inside[sl] * alpha) + patch[sl] * inside[sl] * alpha + ring[sl] * alpha
        (sx, sy) = Q["items"][0][1:3]; dx, dy = cx - sx, cy - sy; D = math.hypot(dx, dy)
        m = np.zeros((H, W), f32)
        if D > R + 5:
            base_a = math.atan2(dy, dx); off = math.asin(R / D)
            for sgn in (-1, 1):
                a = base_a + sgn * off; Lt = math.sqrt(D * D - R * R)
                ex, ey = sx + Lt * math.cos(a), sy + Lt * math.sin(a); bx, by = sx + 16 * math.cos(a), sy + 16 * math.sin(a)
                cv2.line(m, (int(bx * 4), int(by * 4)), (int(ex * 4), int(ey * 4)), 1.0, 2, cv2.LINE_AA, shift=2)
        cv2.circle(m, (int(sx * 4), int(sy * 4)), int(16 * 4), 1.0, 2, cv2.LINE_AA, shift=2)
        img += (cv2.GaussianBlur(m, (0, 0), 0.8) * alpha * 1.1)[..., None] * np.array([1.0, 0.95, 0.88], f32)

    def chroma_bloom(self, img):
        img = bloom(img, 0.5)
        H, W = img.shape[:2]
        sm = np.maximum(cv2.resize(img, (W // 8, H // 8), interpolation=cv2.INTER_AREA) - 1.0, 0)
        acc = np.empty_like(sm)
        for c, s in ((0, 26), (1, 20), (2, 15)): acc[..., c] = cv2.GaussianBlur(sm[..., c], (0, 0), s)
        return img + cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR) * 0.25

    def chroma(self, out):
        W, H = self.L.W, self.L.H; o = out.copy()
        for ch, k in ((0, 1.0018), (2, 0.9982)):
            M = np.float32([[k, 0, (1 - k) * W / 2], [0, k, (1 - k) * H / 2]])
            o[..., ch] = cv2.warpAffine(out[..., ch], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return o

    def overlay(self, out, t, cur, t0, t1):
        L = self.L; W = L.W
        if cur == "night":
            # the label on the eye-view smudge (opening and the loop ending)
            a = ramp(t, 0.15, 0.4) * (1 - ramp(t, T_CAN, T_CAN + 0.3)) if t < T_SW["m31"] else ramp(t, T_BACK + 0.6, T_BACK + 0.9)
            if a > 0.01:
                hud_text(out, "ANDROMEDA GALAXY", P31[0], P31[1] + 70, 30, "Bold", (235, 240, 255), a, 0.12, display=True)
            am = ramp(t, T_MOONS + 0.75, T_MOONS + 0.95) * (1 - ramp(t, T_MOONS1 + 0.2, T_MOONS1 + 0.6))
            if am > 0.01:
                hud_text(out, "6 FULL MOONS WIDE", P31[0], P31[1] - 90, 40, "Black", (255, 222, 120), am, 0.08, display=True)
            if t < T_SW["m31"]:
                pr = 26 + 3 * math.sin(t * 5); ov = np.zeros_like(out[..., 0])
                cv2.circle(ov, (int(P31[0] * 4), int(P31[1] * 4)), int(pr * 4), 1.0, 2, cv2.LINE_AA, shift=2)
                ov = cv2.GaussianBlur(ov, (0, 0), 0.6) * a
                out[:] = out * (1 - ov[..., None] * 0.9) + ov[..., None] * 0.9 * np.array([0.85, 0.95, 1.0], f32)
        else:
            Q = SC[cur]
            a = ramp(t, t0 + 0.15, t0 + 0.45) * (1 - ramp(t, t1 - 0.35, t1 - 0.15)) * (1 - ramp(t, T_WO0, T_WO0 + 0.3))
            if a > 0.01 and Q.get("name"):
                x, ys = W / 2, (262, 338, 386, 432); dy = (1 - a) * 18
                rgba, _ = word_layer(Q["name"], int(L.hud_size * 1.2), W * 0.9, fill=Q["tc"])
                composite(out, rgba, x, ys[0] + dy, a)
                cols = ((255, 222, 120), (255, 255, 255), (200, 225, 255))
                for j, line in enumerate(Q["l"]):
                    hud_text(out, line, x, ys[j + 1] + dy, int(L.hud_size * 0.56), "Black", cols[j], a, 0.06, display=True)
            if a > 0.01 and Q.get("moon"):
                am = a * ramp(t, t0 + 0.6, t0 + 0.9)
                hud_text(out, "MOON", Q["moon"][0], Q["moon"][1] + 46, 26, "Black", (230, 235, 245), am, 0.12, display=True)
            for lab, lx, ly in Q.get("labels", []):
                al = a * ramp(t, t0 + 0.5, t0 + 0.8)
                hud_text(out, lab, lx, ly, 30, "Black", (255, 255, 255), al, 0.10, display=True)
        self.caps.draw(out, t)


def save(im, p): Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p)


def run(stills=None):
    sc = Scene(True); tag = "vert"
    if stills:
        os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
        for t in stills:
            t0 = time.time(); save(sc.frame(t), os.path.join(SCR, "stills", f"{tag}_{t:05.2f}.png"))
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
    if sys.argv[1] == "info":
        print("DUR", DUR, "moons", round(T_MOONS, 2), {k: round(v, 2) for k, v in T_SW.items()}, "wo", round(T_WO0, 2), "back", round(T_BACK, 2))
        for k, deg in (("M31", 3.17), ("M33", 1.18), ("LMC", 10.75), ("SMC", 5.33), ("M51", 11.2 / 60), ("Moon", 0.52)):
            print(k, deg, "deg ->", round(deg * PXD), "px", round(deg / 0.52, 2), "x Moon")
        sys.exit()
    st = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    run(st)
