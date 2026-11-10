"""WHAT IF FAMOUS NEBULAS WERE IN OUR SKY? -- one locked tripod shot of the city (C_city), VFX spectacle style.
Premise: each nebula is moved to D_REF = 15 light-years from Earth (our nearer stellar neighbours) keeping its real size,
so it spans theta = 2 atan(D / 2 d). Lens: gnomonic, f = 960 px (90 deg vertical FOV on 1920 px; same pixel scale in
16:9), so a nebula D ly across is f * D / d px wide. Surface brightness does not change with distance, so each photo keeps
its own brightness (the "camera view"); the narration says the eye would see them much fainter.
  night (real sky around Orion, M42 a 1 deg smudge) -> rush in -> Orion Nebula (77 deg) -> Ring Nebula (3.8 deg) ->
  Pillars of Creation (15 deg) -> Crab Nebula (40 deg, pulsar) -> Carina (we'd be inside it: all-sky) -> "eye view" ghost ->
  phone-camera view -> white-out -> normal night (loops)
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py vert|wide              full render -> SCR/video_<tag>.mp4
  /home/user/ttsenv/bin/python short.py vert 1.0,9.5           stills -> SCR/stills/<tag>_<t>.png
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
from mwsky import canvas, WL, PXD, HB

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S16-nebula-sky"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/C_city.png"
FPS = 30
LEAD, TAIL = 0.25, 1.30
F_PX, D_REF = 960.0, 15.0
M42 = (83.822, -5.391)                                   # RA, Dec (deg)
S0 = 24.0 / 1344.0 * D_REF / 24.0                        # real-distance scale of the Orion sprite (1.02 deg vs 77 deg)

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]


def ang(D): return 2 * math.degrees(math.atan(D / (2 * D_REF)))


# ------------------------------------------------------------------------------------------------ nebulas
# light: colour of the light it casts on the city (normalised sprite mean) x I; beams: palette of the light rays
NEB = {
    "night": dict(name="", I=0.0, gain=1.0, beams=[(0.3, 0.5, 1.0)], bI=0.0, glow=0.0, expo=1.15),
    "orion": dict(name="ORION NEBULA", tc=(255, 190, 120), l2="24 LY ACROSS · REALLY 1,344 LY AWAY", l3=f"IF IT WERE 15 LY AWAY: {ang(24):.0f}° WIDE",
                  I=0.55, gain=0.95, occ=0.4, beams=[(1.0, 0.55, 0.20), (0.25, 0.95, 0.85), (0.85, 0.45, 1.0), (1.0, 0.85, 0.5)], bI=0.55, glow=0.10, expo=0.95),
    "ring":  dict(name="RING NEBULA", tc=(120, 230, 255), l2="~1 LY ACROSS · REALLY ~2,600 LY AWAY", l3=f"IF IT WERE 15 LY AWAY: {ang(1.0):.1f}° · 7 FULL MOONS",
                  I=0.10, gain=1.8, beams=[(0.2, 0.9, 1.0), (1.0, 0.35, 0.25), (0.6, 1.0, 0.6)], bI=0.75, glow=0.30, expo=1.15),
    "pill":  dict(name="PILLARS OF CREATION", tc=(255, 170, 110), l2="~4 LY TALL · REALLY ~6,500 LY AWAY", l3=f"IF IT WERE 15 LY AWAY: {ang(4.0):.0f}° TALL",
                  I=0.22, gain=1.5, occ=0.9, beams=[(1.0, 0.5, 0.15), (0.6, 0.45, 1.0), (0.9, 0.85, 0.75)], bI=0.35, glow=0.22, expo=1.1),
    "crab":  dict(name="CRAB NEBULA", tc=(150, 255, 200), l2="~11 LY ACROSS · REALLY ~6,500 LY AWAY", l3=f"IF IT WERE 15 LY AWAY: {ang(11):.0f}° WIDE",
                  I=0.40, gain=1.15, occ=0.3, beams=[(0.35, 0.8, 1.0), (1.0, 0.55, 0.25), (0.55, 1.0, 0.45), (0.9, 0.5, 1.0)], bI=0.6, glow=0.14, expo=1.0),
    "car":   dict(name="CARINA NEBULA", tc=(255, 160, 90), l2="~230 LY ACROSS · REALLY ~7,500 LY AWAY", l3="IF IT WERE 15 LY AWAY: ALL AROUND US",
                  I=0.60, gain=1.15, beams=[(1.0, 0.5, 0.15), (0.3, 0.6, 1.0), (1.0, 0.8, 0.4)], bI=0.35, glow=0.06, expo=1.0),
}

# ------------------------------------------------------------------------------------------------ timeline
T_RUSH0 = wt("hook", "CLOSE") - 0.05
T_RUSH1 = wt("hook", "STARS") + 0.12                     # Orion arrives (flash)
T_SW = {k: LN[k]["start"] - 0.06 for k in ("ring", "pill", "crab", "car")}
T_PULSAR = wt("crab", "PULSAR")
T_FAINT = wt("eye", "FAINTER") - 0.08
T_CAM = wt("eye", "PHONE") - 0.06
T_THIS = wt("eye", "THIS")
T_BACK = LN["end"]["start"] - 0.08                       # white-out peak -> normal night
T_WO0 = T_BACK - 0.75
COLLAPSE, BLOOM = 0.42, 0.65
SWAPS = [(T_RUSH1, "orion"), (T_SW["ring"], "ring"), (T_SW["pill"], "pill"), (T_SW["crab"], "crab"), (T_SW["car"], "car"), (T_BACK, "night")]
PULSES = [wt("hook", "77°"), wt("ring", "7"), wt("pill", "4"), wt("crab", "30×"), wt("car", "200"), wt("car", "INSIDE"), T_THIS]


def neb_at(t):
    cur, t0 = "night", -10.0
    for ts, k in SWAPS:
        if t >= ts: cur, t0 = k, ts
    nxt = [ts for ts, k in SWAPS if ts > t]
    prev = "night"
    for i, (ts, k) in enumerate(SWAPS):
        if ts == t0 and i > 0: prev = SWAPS[i - 1][1]
    return cur, prev, t0, (nxt[0] if nxt else 1e9)


def back_out(u, s=2.0):
    u = min(max(u, 0.0), 1.0) - 1; return 1 + u * u * ((s + 1) * u + s)


def lerp(a, b, w): return a + (b - a) * w


def pal_list(cols, x):
    C = np.array(cols + [cols[0]], f32); n = len(cols)
    p = (x % 1.0) * n; i = np.floor(p).astype(np.int32); fr = (p - i)[..., None]
    return C[i] * (1 - fr) + C[i + 1] * fr


def palette(x):
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (x[..., None] - np.array([0.0, 0.33, 0.67], f32)))
    return (c ** 2.2).astype(f32)


# ------------------------------------------------------------------------------------------------ scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(vertical); W, H = L.W, L.H
        self.fg = fg = Foreground(FG_PATH, L, lamps=[], hz_frac=0.97)
        self.hz = float(fg.horizon)
        self.C = (540.0, 560.0) if vertical else (960.0, 380.0)
        if vertical: L.cap_y = 1000
        else: L.cap_y = 790; L.cap_size = 104
        yy, xx = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xx, yy
        # ---- night sky: rich deep blue -> violet, warm city glow at the horizon (never black)
        top = 0.0; e = np.clip((self.hz - yy) / (self.hz - top), 0, 1)
        k = np.exp(-e / 0.30)[..., None]
        zen = np.array([0.010, 0.010, 0.072], f32); hor = np.array([0.036, 0.042, 0.185], f32)
        night = zen * (1 - k) + hor * k
        night += np.exp(-((e - 0.45) / 0.22) ** 2)[..., None] * np.array([0.020, 0.004, 0.036], f32)
        night += np.exp(-e / 0.10)[..., None] * np.array([0.050, 0.024, 0.030], f32)          # city light dome
        n = cv2.resize(fbm2((96, 96), 61, 3.0), (W, H), interpolation=cv2.INTER_CUBIC)
        self.night = (night * (1 + 0.06 * n)[..., None]).astype(f32)
        # ---- real sky around Orion: gnomonic camera centred on M42 (north up), at pixel C
        d0 = eq_vec(*M42); npole = np.array([0, 0, 1.0])
        up = npole - d0 * (npole @ d0); up /= np.linalg.norm(up); right = np.cross(up, d0)    # east to the left (sky seen from below)
        self.cam = (d0, right, up)
        z = np.load(os.path.join(SCR, "stars.npz"))
        v = eq_vec(z["ra"], z["dec"]); c = v @ d0
        sx = self.C[0] + F_PX * (v @ right) / np.maximum(c, 1e-3); sy = self.C[1] - F_PX * (v @ up) / np.maximum(c, 1e-3)
        sel = (c > 0.2) & (sx > -5) & (sx < W + 5) & (sy > -5) & (sy < H + 5)
        self.sx, self.sy, mag = sx[sel].astype(f32), sy[sel].astype(f32), z["mag"][sel]
        self.mag = mag
        self.sflux = (3.2 * 10 ** (-0.4 * 0.85 * mag)).astype(f32)
        bv = np.clip(z["ci"][sel], -0.4, 2.0); T = 4600 * (1 / (0.92 * bv + 1.7) + 1 / (0.92 * bv + 0.62))
        cols = np.stack([bbcolor(x) for x in np.clip(T, 2600, 30000)]); yv = cols @ np.array([0.2126, 0.7152, 0.0722])
        cols = np.clip(yv[:, None] + (cols - yv[:, None]) * 1.6, 0.02, None); cols /= (cols @ np.array([0.2126, 0.7152, 0.0722]))[:, None]
        self.scol = cols.astype(f32)
        self.sph = np.random.default_rng(3).uniform(0, 100, len(mag)).astype(f32)
        self.glint = np.where(mag < 1.0)[0]
        # Milky Way (static: the camera is locked; the sky turns too slowly to see in 37 s)
        mw = canvas(os.path.join(SCR, "mw_gal.npz"))
        px_ = (xx - self.C[0]) / F_PX; py_ = -(yy - self.C[1]) / F_PX
        rays = d0[None, None] + px_[..., None] * right[None, None] + py_[..., None] * up[None, None]
        rays /= np.linalg.norm(rays, axis=-1, keepdims=True)
        g = rays @ EQ2GAL.T
        l = np.arctan2(g[..., 1], g[..., 0]); b = np.arcsin(np.clip(g[..., 2], -1, 1))
        mx = (WL / 2 + np.degrees(l) * PXD) % WL; my = HB / 2 - np.degrees(b) * PXD
        self.mw = cv2.remap(mw, mx.astype(f32), my.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP) * 1.6
        # ---- nebula sprites (true size for the premise; Carina: all-sky backdrop)
        sp = np.load(os.path.join(SCR, "sprites.npz"))
        self.sp = {}
        for kk in ("orion", "ring", "pill", "crab", "car"):
            im = sp[kk].astype(f32)
            h, w = im.shape[:2]
            if kk == "car":                                                    # feathered edges for the bloom-in
                fy = np.minimum(np.arange(h), np.arange(h)[::-1])[:, None]; fx = np.minimum(np.arange(w), np.arange(w)[::-1])[None]
                im = im * (smooth(0, 160, fx) * smooth(0, 160, fy))[..., None].astype(f32)
            sig = max(1.5, 0.02 * max(h, w))
            lo = cv2.GaussianBlur(im, (0, 0), sig)
            light = sp[kk + "_light"]; light = light / max(light.max(), 1e-6)
            self.sp[kk] = dict(m=sp[kk + "_m"].astype(f32), img=im, lo=lo, hi=im - lo, st=sp[kk + "_st"], sc=sp[kk + "_sc"], light=light.astype(f32), w=w, h=h)
        self.sp["night"] = self.sp["orion"]
        # placements: (centre x, centre y, base scale) in this layout
        cx, cy = self.C
        if vertical:
            self.place = dict(night=(cx, cy, S0), orion=(cx, cy, 1.0), ring=(cx, cy + 20, 1.0), pill=(540.0, 640.0, 1.0),
                              crab=(cx, cy, 1.0), car=(cx, 700.0, 1.32))
        else:
            self.place = dict(night=(cx, cy, S0), orion=(cx, cy, 1.0), ring=(cx, cy, 1.0), pill=(960.0, 400.0, 1.0),
                              crab=(cx, cy, 1.0), car=(cx, 430.0, 1.0))
        self.car_anchor = (0.5, 0.36)                                          # Cosmic Cliffs edge (fraction of the sprite)
        self.shim = fbm2((256, 256), 81, 2.0)
        r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 9 + r.uniform(-0.2, 0.2), w=r.uniform(0.10, 0.20), I=r.uniform(0.7, 1.2), hue=r.uniform(0, 1),
                           ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(9)]
        hw, hh = W // 2, H // 2
        hy, hx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.hx, self.hy = hx, hy
        # ---- city: night grade with its own lights; relit by the nebula
        a = fg.a; self.a = a[..., None]
        rgb = fg.rgb; f = fg.flat; y = lum(f)[..., None]
        mxc = rgb.max(2); warm = rgb[..., 0] - rgb[..., 2]
        win = (smooth(0.10, 0.42, mxc) * smooth(0.0, 0.08, warm)).astype(f32)
        self.lights = (rgb * win[..., None] * 2.6 + win[..., None] * np.array([0.20, 0.10, 0.03], f32)).astype(f32)
        self.base = ((f * 0.35 + y * 0.65) * np.array([0.30, 0.36, 0.75], f32) * 0.30 * (1 - win[..., None])).astype(f32)
        self.alb = np.clip(f * (1 - 0.7 * win[..., None]), 0, 1).astype(f32)
        sk = np.clip((self.hz + 200 - yy) / (self.hz + 200 - fg.skyline.min()), 0, 1)       # higher = more sky-facing light
        self.skyfac = (0.35 + 0.65 * sk)[..., None].astype(f32)
        sh = np.zeros_like(a); sh[8:] = a[:-8]
        self.rim = (cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 2.5) * a)[..., None].astype(f32)
        self.wph = fbm2((64, 64), 7, 0.5)
        emph = {"ORION", "77°", "RING", "7", "PILLARS", "CREATION", "4", "CRAB", "30×", "CARINA", "200", "INSIDE", "FAINTER", "CAMERA", "THIS", "FAR"}
        self.caps = Captions(L, WORDS, emphasis=emph)

    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    # -------------------------------------------------------------------------------------------- sky stars
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
            splat(acc, self.sx[i], self.sy[i], 50, lambda d, dx, dy: ((np.exp(-np.abs(dy) / 0.8) * np.exp(-np.abs(dx) / 14) + np.exp(-np.abs(dx) / 0.8) * np.exp(-np.abs(dy) / 14)) * g)[..., None] * c)
        st = cv2.GaussianBlur(acc, (0, 0), 0.75) * 2.2
        big = acc * (acc.max(2, keepdims=True) > 0.3)
        return st + cv2.GaussianBlur(big, (0, 0), 2.5) * 2.0

    # -------------------------------------------------------------------------------------------- nebula sprite
    def matrix(self, key, s, rot, ox=0.0, oy=0.0):
        S = self.sp[key]; cx, cy, s0 = self.place[key]
        ax, ay = (self.car_anchor if key == "car" else (0.5, 0.5))
        sc = s0 * s; c, sn = math.cos(rot) * sc, math.sin(rot) * sc
        px, py = ax * S["w"], ay * S["h"]
        return np.float32([[c, -sn, cx + ox - (c * px - sn * py)], [sn, c, cy + oy - (sn * px + c * py)]])

    def sprite(self, key, t, s, rot, gain):
        """warp the nebula into the frame: two depth layers drifting against each other (parallax), shimmer on the detail"""
        W, H = self.L.W, self.L.H; S = self.sp[key]
        self.occ = None
        if s * self.place[key][2] < 1e-3 or gain <= 0: return np.zeros((H, W, 3), f32), None
        dep = 1.0 if key != "night" else 0.0
        px, py = 5 * math.sin(0.33 * t) * dep, 3.5 * math.cos(0.27 * t) * dep
        if key == "car": px += -14 * t + 60 * math.sin(0.11 * t)                # slow drift of the all-sky glow
        out = np.zeros((H, W, 3), f32)
        eff = s * self.place[key][2]
        for lay, sgn in ((S["lo"], 1.0), (S["hi"], -1.0)):
            src = lay; M = self.matrix(key, s, rot, px * sgn, py * sgn)
            if eff < 0.6:                                                     # pre-filter strong minification
                k = max(eff / 0.8, 1.0 / max(S["w"], S["h"]))
                nw, nh = max(2, int(S["w"] * k)), max(2, int(S["h"] * k))
                src = cv2.resize(lay, (nw, nh), interpolation=cv2.INTER_AREA)
                M = M.copy(); M[:, 0] *= S["w"] / nw; M[:, 1] *= S["h"] / nh
            out += cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        if key in ("orion", "crab", "car") and eff > 0.5:                        # gas shimmer
            u = (self.xx * 0.10 + t * 6) % 256; v = (self.yy * 0.10 - t * 4) % 256
            n = cv2.remap(self.shim, u.astype(f32), v.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
            out = cv2.remap(out, self.xx + n * 1.6, self.yy + n * 1.1, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        out = np.maximum(out, 0) * gain
        Mm = self.matrix(key, s, rot, px, py)
        msrc = S["m"]
        if eff < 0.6:
            k = max(eff / 0.8, 1.0 / max(S["w"], S["h"])); nw, nh = max(2, int(S["w"] * k)), max(2, int(S["h"] * k))
            msrc = cv2.resize(msrc, (nw, nh), interpolation=cv2.INTER_AREA); Mm = Mm.copy(); Mm[:, 0] *= S["w"] / nw; Mm[:, 1] *= S["h"] / nh
        self.occ = cv2.warpAffine(msrc, Mm, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        return out, self.matrix(key, s, rot, -px, -py)

    def twinkles(self, img, key, M, t, gain):
        """the photo's own brightest stars twinkle with chromatic 4-point spikes"""
        if M is None or gain <= 0: return
        S = self.sp[key]; W, H = self.L.W, self.L.H
        sc = math.hypot(M[0, 0], M[1, 0])
        for j, (x, y, v) in enumerate(S["st"]):
            fx = M[0, 0] * x + M[0, 1] * y + M[0, 2]; fy = M[1, 0] * x + M[1, 1] * y + M[1, 2]
            if not (0 <= fx < W and 0 <= fy < H): continue
            tw = (0.5 + 0.5 * math.sin(t * (2.0 + 1.3 * (j % 5)) + j * 2.1)) ** 3
            g = gain * v * (0.15 + 0.85 * tw) * 0.9 * min(1.0, sc * 1.5)
            if g < 0.02: continue
            c = S["sc"][j] * 0.5 + 0.5; L_ = 10 + 22 * v
            splat(img, fx, fy, 70, lambda d, dx, dy: (np.exp(-d / 1.3) * 2.0 * g + (np.exp(-np.abs(dy) / 0.9) * np.exp(-np.abs(dx) / L_) + np.exp(-np.abs(dx) / 0.9) * np.exp(-np.abs(dy) / L_)) * g * 0.7)[..., None] * c)

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

    # -------------------------------------------------------------------------------------------- frame
    def state(self, key, t, t0, t1):
        """-> sprite scale, rotation, intensity multiplier, collapse progress"""
        s, rot, I = 1.0, 0.0, 1.0
        if key == "night":
            if t < T_RUSH1:                                                   # the opening rush towards us
                u = max(0.0, (t - T_RUSH0) / (T_RUSH1 - T_RUSH0))
                s = math.exp(math.log(1 / S0) * min(u, 1) ** 2.4)
            return s, 0.0, 1.0, 0.0
        u_in = (t - t0) / BLOOM
        if key == "orion": s = 0.92 + 0.08 * back_out(u_in, 3.0)
        elif key == "car": s = 0.45 + 0.55 * back_out(u_in, 1.6); I = min(1.0, max(u_in * 2.5, 0.0))
        else: s = back_out(u_in); I = 0.4 + 0.6 * min(max(u_in * 3, 0), 1)
        s *= 1 + 0.012 * math.sin(t * 0.9)
        rot = math.radians(0.6) * math.sin(0.21 * t + len(key))
        col_u = 0.0 if (t1 > 1e8 or key == "car") else max(0.0, 1 - (t1 - t) / COLLAPSE)
        if col_u > 0:
            if col_u < 0.45: s *= 1 + 0.22 * ease(col_u / 0.45)
            else: v = (col_u - 0.45) / 0.55; s *= 1.22 * (1 - ease(v) ** 0.7) + 0.01
            rot += 1.8 * col_u ** 2; I *= 1 + 2.5 * col_u ** 2
        return s, rot, I, col_u

    def frame(self, t):
        L = self.L; W, H = L.W, L.H
        cur, prev, t0, t1 = neb_at(t)
        P, Q = NEB[prev], NEB[cur]
        w = ramp(t, t0 - 0.12, t0 + 0.5) if t0 > 0 else 1.0
        s, rot, I, col_u = self.state(cur, t, t0, t1)
        pulse = 1 + 0.06 * math.sin(2 * math.pi * t / 1.7) + sum(0.35 * math.exp(-((t - tp) / 0.22) ** 2) for tp in PULSES)
        ghost = ramp(t, T_FAINT, T_FAINT + 0.45) * (1 - ramp(t, T_CAM, T_CAM + 0.06))
        blaze = ramp(t, T_CAM, T_CAM + 0.1) * (1 - ramp(t, T_WO0, T_BACK)) * (1 + 0.5 * math.exp(-max(t - T_THIS, 0) / 0.5) * (t > T_THIS))
        # ---- sky
        dim = 1.0 - 0.35 * (Q["I"] * w + P["I"] * (1 - w))
        sky = self.night + self.mw * (1 - 0.4 * (Q["I"] * w + P["I"] * (1 - w))) + self.stars(t, dim)
        g = Q["gain"] * I * pulse * (1 + 0.35 * blaze)
        neb, M = self.sprite(cur, t, s, rot, g)
        cx, cy, _ = self.place[cur]
        S = self.sp[cur]
        Rsz = 0.5 * max(S["w"], S["h"]) * self.place[cur][2] * s
        if cur == "crab":                                                     # the pulsar (30/s for real; shown as a 7.5 Hz throb)
            fxp = M[0, 0] * 0.50 * S["w"] + M[0, 1] * 0.565 * S["h"] + M[0, 2]; fyp = M[1, 0] * 0.50 * S["w"] + M[1, 1] * 0.565 * S["h"] + M[1, 2]
            beat = 0.5 + 0.5 * math.cos(2 * math.pi * 7.5 * t)
            pk = (1.0 + 2.5 * ramp(t, T_PULSAR - 0.1, T_PULSAR + 0.2)) * (0.25 + 0.75 * beat) * I * s
            splat(neb, fxp, fyp, 160, lambda d, dx, dy: (np.exp(-d / 2.0) * 6 + np.exp(-d / 14) * 0.9 + np.exp(-d / 60) * 0.18
                                                       + (np.exp(-np.abs(dy) / 1.2) * np.exp(-np.abs(dx) / 70) + np.exp(-np.abs(dx) / 1.2) * np.exp(-np.abs(dy) / 70)) * 1.2)[..., None] * pk * np.array([0.7, 0.85, 1.0], f32))
        self.twinkles(neb, cur, M, t, I * (1 if cur != "night" else 0.0))
        # nebula glow in the sky + light rays (half res)
        dx, dy = self.hx - cx, self.hy - cy; d = np.sqrt(dx * dx + dy * dy)
        lc = S["light"]
        aure = (np.exp(-np.maximum(d - Rsz * 0.4, 0) / (120 + 0.6 * Rsz)) * Q["glow"] * 2.0 + 0.015 * Q["I"]) * I
        if cur == "night": aure = np.exp(-d / 30) * 0.12 * (s > 1.5)
        lay = aure[..., None] * lc * 0.25 + self.rays(t, P, Q, w, cx, cy, Rsz, col_u, Q["bI"] * (1 + 1.2 * col_u) * min(1.0, I))
        if prev != "night" and w < 1:                                          # previous nebula's sky glow fading out
            pl = self.sp[prev]["light"]; lay += (0.08 * P["I"] * (1 - w)) * pl * 0.25
        neb = neb + self.up(lay * pulse)
        if ghost > 0:                                                          # the eye's view: dim grey ghosts
            yv = lum(neb)[..., None]
            neb = neb * (1 - ghost) + yv * np.array([0.80, 0.90, 1.0], f32) * 0.22 * ghost
        if self.occ is not None and Q.get("occ", 0) > 0: sky = sky * (1 - Q["occ"] * min(1.0, I) * (1 - ghost) * self.occ[..., None])
        sky = sky + neb
        # ---- city: night grade, windows on, relit by the nebula
        lw = (Q["I"] * w * I + P["I"] * (1 - w)) * (1 - 0.75 * ghost) * (0.9 + 0.1 * pulse) * (1 + 0.3 * blaze)
        lcol = S["light"] * w + self.sp[prev]["light"] * (1 - w)
        lcol = np.clip(lcol * 1.15, 0, None)
        fgc = self.base + self.alb * self.skyfac * lcol * lw * 1.1 + self.rim * lcol * (0.4 + 1.6 * lw) * 0.6
        flick = 1 + 0.04 * math.sin(t * 3.1)
        fgc = fgc + self.lights * flick
        img = sky * (1 - self.a) + fgc * self.a
        # ---- swap flash + chromatic shockwave
        for ts, k in SWAPS:
            u = t - ts
            if -0.05 < u < 1.4:
                fc = 0.45 + 0.55 * self.sp[k]["light"] if k != "night" else np.array([1.0, 0.95, 0.9], f32)
                img += (2.0 * math.exp(-max(u, 0) / 0.09) * ease((u + 0.05) / 0.05)) * fc
                if k == "night": continue
                pc = self.place[k]
                R = 2400 * (max(u, 0) / 1.4) ** 0.6; wdt = 18 + 60 * u
                dd = np.sqrt((self.hx - pc[0]) ** 2 + (self.hy - pc[1]) ** 2)
                ring = np.zeros(dd.shape + (3,), f32)
                for ch, off in ((0, 12), (1, 0), (2, -12)):
                    ring[..., ch] = np.exp(-((dd - R - off) / wdt) ** 2) * 2.0 * math.exp(-max(u, 0) / 0.55)
                img += self.up(ring)
        if T_CAM - 0.02 < t < T_CAM + 0.5:                                    # phone shutter flash
            img += 1.6 * math.exp(-max(t - T_CAM, 0) / 0.07)
        if T_WO0 < t < T_BACK:                                                # white-out into the normal night
            v = ease((t - T_WO0) / (T_BACK - T_WO0)); img = img + (24 * v ** 2.5) * np.array([1.0, 0.94, 0.88], f32)
        img = self.chroma_bloom(img)
        expo = lerp(P["expo"], Q["expo"], w)
        out = tonemap(img, expo)
        y_ = out.mean(2, keepdims=True); out = np.clip(y_ + (out - y_) * 1.25, 0, 1)
        out = self.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.14)
        self.overlay(out, t, cur, t0, ghost)
        return out

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

    def overlay(self, out, t, cur, t0, ghost):
        L = self.L; W, H = L.W, L.H
        # small label on the real-distance smudge (opening and loop ending)
        if cur == "night":
            a = ramp(t, 0.15, 0.4) * (1 - ramp(t, T_RUSH0 - 0.1, T_RUSH0 + 0.1)) if t < T_RUSH1 else ramp(t, T_BACK + 0.9, T_BACK + 1.2)
            if a > 0.01:
                x, y = self.C[0], self.C[1] + 46
                hud_text(out, "ORION NEBULA · 1,344 LY", x, y, 30 if L.vertical else 28, "Bold", (235, 240, 255), a, 0.12, display=True)
        else:
            Q = NEB[cur]
            if L.vertical: x, ys = W / 2, (300, 380, 436)
            else: x, ys = 430, (110, 180, 228)
            a = ramp(t, t0 + 0.15, t0 + 0.45)
            nxt = [ts for ts, k in SWAPS if ts > t]
            if nxt: a *= 1 - ramp(t, nxt[0] - 0.35, nxt[0] - 0.15)
            a *= 1 - ramp(t, T_WO0, T_WO0 + 0.3)
            if a > 0.01:
                dy = (1 - a) * 18
                big = int(L.hud_size * (1.35 if len(Q["name"]) < 14 else 1.12))
                rgba, _ = word_layer(Q["name"], big, W * 0.9 if L.vertical else 780, fill=Q["tc"])
                composite(out, rgba, x, ys[0] + dy, a)
                hud_text(out, Q["l2"], x, ys[1] + dy, int(L.hud_size * 0.56), "Black", (255, 255, 255), a, 0.06, display=True)
                hud_text(out, Q["l3"], x, ys[2] + dy, int(L.hud_size * 0.56), "Black", (255, 222, 120), a, 0.06, display=True)
                if cur == "crab" and t > T_PULSAR - 0.1:
                    ap = a * ramp(t, T_PULSAR - 0.1, T_PULSAR + 0.15)
                    hud_text(out, "PULSAR: 30 FLASHES A SECOND", x, ys[2] + 56 + dy, int(L.hud_size * 0.46), "Bold", (170, 220, 255), ap, 0.06, display=True)
        # phone-camera viewfinder ("your phone camera would see this")
        if T_CAM - 0.02 < t < T_WO0:
            a = ramp(t, T_CAM, T_CAM + 0.1) * (1 - ramp(t, T_WO0 - 0.35, T_WO0))
            self.viewfinder(out, a, t)
        self.caps.draw(out, t)

    def viewfinder(self, out, a, t):
        W, H = self.L.W, self.L.H
        m = 70 if self.L.vertical else 60; ln = 90; th = 6
        c = np.array([1.0, 1.0, 1.0], f32)
        top = int(0.13 * H) if self.L.vertical else 40; bot = int(0.78 * H) if self.L.vertical else H - 40
        for (x, y, sx, sy) in ((m, top, 1, 1), (W - m, top, -1, 1), (m, bot, 1, -1), (W - m, bot, -1, -1)):
            x0, x1 = sorted((x, x + sx * ln)); y0, y1 = sorted((y, y + sy * th))
            out[y0:y1, x0:x1] = out[y0:y1, x0:x1] * (1 - a) + c * a
            x0, x1 = sorted((x, x + sx * th)); y0, y1 = sorted((y, y + sy * ln))
            out[y0:y1, x0:x1] = out[y0:y1, x0:x1] * (1 - a) + c * a
        # focus square on the sky, red REC dot
        cx, cy = int(self.C[0]), int(self.C[1]); r = 70
        for (x0, x1, y0, y1) in ((cx - r, cx + r, cy - r, cy - r + 4), (cx - r, cx + r, cy + r - 4, cy + r), (cx - r, cx - r + 4, cy - r, cy + r), (cx + r - 4, cx + r, cy - r, cy + r)):
            out[y0:y1, x0:x1] = out[y0:y1, x0:x1] * (1 - a) + np.array([1.0, 0.85, 0.2], f32) * a
        if math.sin(t * 6) > -0.3:
            rx, ry = m + 30, top + 50
            yy, xx = np.mgrid[ry - 14:ry + 15, rx - 14:rx + 15]
            dsk = ((xx - rx) ** 2 + (yy - ry) ** 2 <= 144)[..., None] * a
            out[ry - 14:ry + 15, rx - 14:rx + 15] = out[ry - 14:ry + 15, rx - 14:rx + 15] * (1 - dsk) + np.array([1.0, 0.15, 0.1], f32) * dsk


def save(im, p): Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p)


def run(vertical, stills=None):
    sc = Scene(vertical); tag = "vert" if vertical else "wide"
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
        print("DUR", DUR, "rush", round(T_RUSH0, 2), round(T_RUSH1, 2), {k: round(v, 2) for k, v in T_SW.items()},
              "faint", round(T_FAINT, 2), "cam", round(T_CAM, 2), "back", round(T_BACK, 2))
        for k, D in (("orion", 24), ("ring", 1), ("pill", 4), ("crab", 11), ("car", 230)): print(k, D, "ly ->", round(ang(D), 1), "deg", round(F_PX * D / D_REF), "px")
        sys.exit()
    vert = sys.argv[1] != "wide"
    st = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    run(vert, st)
