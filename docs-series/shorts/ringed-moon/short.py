"""WHAT IF THE MOON HAD RINGS? -- one LOCKED tripod shot of the snowy mountain village (02_snowy_mountain_village) at
night, BATCH4 swap format. The Moon is drawn at its TRUE angular size (0.518 deg) through a long telephoto lens
(f = 13,000 px, the frame is ~4.8 deg wide); its rings are Saturn's real radial ring profile (C ring to F ring) scaled
from Saturn's radius to the Moon's, so they span 2 x 2.27 Moon radii = 1.18 deg (science.py).
  normal Moon -> ringed Moon rising over the ridge -> the rings' shadow on the disc (side lighting) -> the rings turn
  edge-on (a hairline of light) -> rings wide open at full Moon, ~5.5x the moonlight, the village glows -> white-out
  -> our plain Moon (loops)
Every swap: tinted flash + chromatic shockwave + soft beams, the village is relit. The Moon and rings sit BEHIND the
plate (opaque where alpha > 0.9). Ring rendering: rings.py (copied from ../planets-as-moon/planets.py).
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py info
  /home/user/ttsenv/bin/python short.py stills 1.0,9.5        -> SCR/stills/vert_<t>.png
  /home/user/ttsenv/bin/python short.py seg                   restart-safe segment render -> SCR/video_vert.mp4
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401
import numpy as np, cv2
from PIL import Image
from lib.core import f32, Layout, ramp, smooth, ease, lum
from lib.foreground import Foreground
from lib.sky import SkyCam, StarSky
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish
from lib.audio import place
import rings as RG
from rings import Body, pole_vec, frame_of
import science as SC

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B4-ringed-moon"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/02_snowy_mountain_village.png"
FPS = 30
LEAD, TAIL = 0.25, 1.30
F_PX = 13000.0
RP = F_PX * math.tan(math.asin(SC.R_MOON / SC.D_MOON))         # 58.8 px: the Moon's true radius on screen
C = (590.0, 640.0)                                             # where the Moon hangs
RISE0 = (800.0, 1125.0)                                        # behind the ridge, right of the big pine

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}


def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]


def sun_vec(phase_deg, pa_deg):
    """direction to the Sun (camera frame: x right, y down, z away). phase angle; pa = screen direction the light comes
    from (0 = from the left, 90 = from below)"""
    p, a = math.radians(phase_deg), math.radians(pa_deg)
    return np.array([-math.sin(p) * math.cos(a), math.sin(p) * math.sin(a), -math.cos(p)])


# ------------------------------------------------------------------------------------------------ the beats
# tip: ring opening (deg, towards the viewer), roll: ring-plane tilt on screen, phase/pa: lighting, E: moonlight (x full
# Moon today), sky: sky-brightness factor, win: window glow
ST = {
    "now": dict(name="OUR MOON", l2="0.52° WIDE", l3="384,400 KM AWAY", tc=(225, 235, 255), rings=False, tip=26.7, roll=-24,
                phase=6, pa=20, E=1.0, sky=1.0, fl=(0.8, 0.88, 1.0), beams=[(0.55, 0.65, 1.0), (0.80, 0.70, 1.0), (0.50, 0.90, 1.0)]),
    "ring": dict(name="RINGED MOON", l2="RINGS 1.2° ACROSS · 2.3× ITS WIDTH", l3="SATURN'S RINGS, SCALED TO THE MOON", tc=(255, 222, 160),
                 rings=True, tip=26.7, roll=-24, phase=6, pa=20, E=2.6, sky=1.5, fl=(1.0, 0.9, 0.7),
                 beams=[(1.0, 0.85, 0.55), (0.75, 0.80, 1.0), (1.0, 0.70, 0.45), (0.9, 0.9, 1.0)]),
    "shad": dict(name="RING SHADOW", l2="SUNLIGHT FROM THE SIDE", l3="A DARK BAND ACROSS THE DISC", tc=(205, 220, 255), rings=True,
                 tip=26.7, roll=-24, phase=32, pa=114, E=2.0, sky=1.35, fl=(0.8, 0.85, 1.0),
                 beams=[(0.55, 0.65, 1.0), (0.85, 0.70, 1.0), (0.45, 0.85, 1.0)]),
    "edge": dict(name="EDGE-ON", l2="1.2° LONG · ONLY METRES THICK", l3="SATURN'S RINGS DO THIS EVERY ~15 YEARS", tc=(235, 240, 255),
                 rings=True, tip=0.35, roll=-24, phase=12, pa=-55, E=1.0, sky=1.0, fl=(0.85, 0.9, 1.0),
                 beams=[(0.7, 0.8, 1.0), (1.0, 0.9, 0.7), (0.6, 0.7, 1.0)]),
    "light": dict(name="BRIGHTER NIGHTS", l2="~5.5× TODAY'S FULL-MOON LIGHT", l3="ICY RINGS REFLECT 4× MORE THAN ROCK", tc=(255, 230, 170),
                  rings=True, tip=26.7, roll=-24, phase=3, pa=20, E=5.5, sky=2.6, fl=(1.0, 0.95, 0.8),
                  beams=[(1.0, 0.9, 0.6), (0.8, 0.85, 1.0), (1.0, 0.75, 0.5), (0.95, 0.95, 1.0)]),
}
ST["end"] = dict(ST["now"])
T_SW = dict(ring=LN["ring"]["start"] - 0.06, shad=LN["shad"]["start"] - 0.06, edge=LN["edge"]["start"] - 0.06,
            light=LN["light"]["start"] - 0.06)
T_GONE = wt("end", "GONE") - 0.04                              # "Then... they're GONE": white-out, back to our Moon
T_WO0 = LN["end"]["start"] - 0.10
SWAPS = [(T_SW["ring"], "ring"), (T_SW["shad"], "shad"), (T_SW["edge"], "edge"), (T_SW["light"], "light"), (T_GONE, "end")]
T_RISE1 = wt("ring_3", "MORE") + 0.2                           # the rise finishes as "more than twice as wide" starts
T_EDGE1 = wt("edge", "EDGE-ON") + 0.45                         # the rings close to a hairline by "edge-on"
PULSES = [wt("hook_2", "RINGS"), wt("ring", "RINGS"), wt("ring_4", "HALO"), wt("shad", "SHADOW"), wt("edge_2", "LIGHT"),
          wt("light_2", "BRIGHTER"), wt("light_3", "GLOWS")]


def stage_at(t):
    cur, t0, prev = "now", -10.0, None
    for ts, k in SWAPS:
        if t >= ts: prev, cur, t0 = cur, k, ts
    nxt = [ts for ts, k in SWAPS if ts > t]
    return cur, prev, t0, (nxt[0] if nxt else 1e9)


def lerp(a, b, w): return tuple(x + (y - x) * w for x, y in zip(a, b)) if isinstance(a, tuple) else a + (b - a) * w


def palette(x):
    x = np.asarray(x, f32)[..., None]
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (x - np.array([0.0, 0.33, 0.67], f32)))
    return (c ** 2.2).astype(f32)


def pal_list(cols, x):
    Cc = np.array(cols + [cols[0]], f32); n = len(cols)
    p = (np.asarray(x) % 1.0) * n; i = np.floor(p).astype(np.int32); fr = (p - i)[..., None]
    return Cc[i] * (1 - fr) + Cc[i + 1] * fr


def back_out(u, s=1.6):
    u = min(max(u, 0.0), 1.0) - 1; return 1 + u * u * ((s + 1) * u + s)


def state(t):
    """the continuous look at time t: the moon's position, ring geometry, lighting, moonlight level"""
    cur, prev, t0, t1 = stage_at(t)
    S = ST[cur]; P = ST[prev] if prev else S
    w = ramp(t, t0 - 0.05, t0 + 0.7) if prev else 1.0
    tip = lerp(P["tip"], S["tip"], w); phase = lerp(P["phase"], S["phase"], w); pa = lerp(P["pa"], S["pa"], w)
    if cur == "edge":                                              # the rings swing slowly shut
        u = ease((t - t0) / (T_EDGE1 - t0)); tip = P["tip"] + (S["tip"] - P["tip"]) * u ** 1.2
    if cur == "light":
        u = ease((t - t0) / 1.4); tip = P["tip"] + (S["tip"] - P["tip"]) * u
    E = lerp(P["E"], S["E"], ramp(t, t0, t0 + (1.6 if cur == "light" else 0.8)) if prev else 1.0)
    sky = lerp(P["sky"], S["sky"], ramp(t, t0, t0 + 1.2) if prev else 1.0)
    pos = C
    if cur == "ring":                                              # moonrise over the ridge
        u = ease((t - t0) / (T_RISE1 - t0))
        u = 1 - (1 - min(max((t - t0) / (T_RISE1 - t0), 0), 1)) ** 1.6
        pos = (RISE0[0] + (C[0] - RISE0[0]) * u, RISE0[1] + (C[1] - RISE0[1]) * u)
    return dict(cur=cur, prev=prev, t0=t0, t1=t1, S=S, P=P, w=w, tip=max(tip, 0.25), phase=phase, pa=pa, E=E, sky=sky, pos=pos,
                rings=S["rings"])


class Scene:
    def __init__(self, vertical=True):
        assert vertical, "9:16 only"
        self.L = L = Layout(True); W, H = L.W, L.H; self.W, self.H = W, H
        self.fg = fg = Foreground(FG_PATH, L, lamps=[], hz_frac=0.68)
        self.a = np.where(fg.a > 0.9, 1.0, fg.a).astype(f32)          # the plate is fully opaque where alpha > 0.9
        yy, xx = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xx, yy
        sky_bot = 1130.0
        el = np.clip((sky_bot - yy) / sky_bot, 0, 1)
        k = np.exp(-el / 0.30)[..., None]
        zen = np.array([0.0035, 0.0065, 0.026], f32); hor = np.array([0.020, 0.030, 0.070], f32)
        self.night = (zen * (1 - k) + hor * k).astype(f32)
        self.cam = SkyCam(W, H, sky_bot, 1400.0)
        self.stars = StarSky(42)
        # extinction for the rising Moon (it stays a few degrees up: the telephoto frame is ~4.8 deg wide)
        self.sky_bot = sky_bot
        # ---- the village: lit windows (warm bright pixels of the plate) + their spill on the snow
        src = np.clip(fg.rgb, 0, 1) ** (1 / 2.2)
        rr, bb = src[..., 0], src[..., 2]
        win = np.clip((rr - 0.45) / 0.25, 0, 1) * np.clip((rr / (bb + 0.02) - 1.5) / 0.8, 0, 1) * self.a
        self.win = cv2.GaussianBlur(win, (0, 0), 0.7).astype(f32)
        self.win_rgb = (fg.rgb * self.win[..., None]).astype(f32)
        spill = cv2.GaussianBlur(self.win, (0, 0), 30) + cv2.GaussianBlur(self.win, (0, 0), 90) * 0.6
        self.spill = (spill / max(spill.max(), 1e-4) * self.a).astype(f32)
        self.base = (fg.rgb * (1 - self.win[..., None])).astype(f32)
        Y = lum(fg.rgb)
        self.snow = (smooth(0.25, 0.65, Y) * (1 - self.win) * self.a).astype(f32)          # bright snow catches moonlight
        sh = np.zeros_like(self.a); sh[8:] = self.a[:-8]
        self.rim = (cv2.GaussianBlur(np.clip(self.a - sh, 0, 1), (0, 0), 2.5) * self.a).astype(f32)
        gl = np.random.default_rng(11)
        ys, xs = np.nonzero(self.snow > 0.6)
        pick = gl.choice(len(xs), min(2500, len(xs)), replace=False)
        self.gx, self.gy = xs[pick], ys[pick]; self.gph = gl.uniform(0, 6.28, len(pick)); self.gfr = gl.uniform(0.3, 1.2, len(pick))
        # ---- the Moon (familiar face kept: globe frame fixed; the ring plane tilts on its own)
        RG.set_sun(sun_vec(6, 20))
        self.moon = Body("moon", "8k_moon.jpg", RP, pole_vec(-24, 26.7), model="rock", surf=3.4, detail=0.0, rings="saturn", ss=3)
        self.moon.Mg = frame_of(pole_vec(-8, 4))
        self.moon0 = Body("moon0", "8k_moon.jpg", RP, pole_vec(-8, 4), model="rock", surf=3.4, detail=0.0, ss=3)
        r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 8 + r.uniform(-0.25, 0.25), w=r.uniform(0.10, 0.20), I=r.uniform(0.8, 1.2), hue=r.uniform(0, 1),
                           ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(8)]
        hw, hh = W // 2, H // 2
        self.hy, self.hx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        emph = {"RINGS", "SATURN'S", "MOUNTAINS", "TWICE", "HALO", "SHADOW", "STRIPE", "EDGE-ON", "RAZOR-THIN", "LIGHT",
                "FIVE", "BRIGHTER", "GLOWS", "GONE", "LONELY", "MOON"}
        self.caps = Captions(L, WORDS, emphasis=emph)
        L.cap_y = 1240

    # -------------------------------------------------------------------------------------------- layers
    def beams_layer(self, t, cx, cy, amt, cols):
        dx, dy = self.hx - cx, self.hy - cy
        d = np.sqrt(dx * dx + dy * dy) + 1e-3; phi = np.arctan2(dy, dx)
        acc = np.zeros(d.shape + (3,), f32)
        rad = smooth(RP * 2.3, RP * 3.2, d) * (np.exp(-d / 900) * 0.9 + 0.1)
        for b in self.beams:
            a = b["a"] + 0.05 * t * b["sp"]
            dp = (phi - a + np.pi) % (2 * np.pi) - np.pi
            wd = b["w"] * (1 + 0.25 * math.sin(t * 0.9 * b["sp"] + b["ph"]))
            g = np.exp(-(dp / wd) ** 2 * 1.6)
            I = b["I"] * (0.72 + 0.28 * math.sin(t * 1.3 * b["sp"] + b["ph"] * 2))
            x = (b["hue"] + dp / wd * 0.3 + 0.04 * t) % 1.0
            acc += pal_list(cols, x) * (g * I)[..., None]
        return cv2.resize(acc * rad[..., None] * 0.30 * amt, (self.W, self.H), interpolation=cv2.INTER_LINEAR)

    def ext_col(self, y):
        """reddening + dimming of the Moon low over the ridge (a few degrees up)"""
        el = max((self.sky_bot + 140 - y) / F_PX, 0.0)
        eld = max(math.degrees(el), 0.3) + 1.5
        X = 1 / (math.sin(math.radians(eld)) + 0.50572 * (eld + 6.07995) ** -1.6364)
        tau = np.array([0.05, 0.075, 0.14], f32)
        e = np.exp(-X * tau) ** 0.45; e = e / e.max() * (0.70 + 0.30 * e.max())
        return (e * np.array([0.97, 1.0, 1.06], f32)).astype(f32)

    def relight(self, t, E, s):
        """the village under moonlight E (x today's full Moon); windows stay warm"""
        g = E ** 0.62
        out = self.base * np.array([0.62, 0.74, 1.05], f32) * (0.20 + 0.20 * g)
        out += self.snow[..., None] * np.array([0.030, 0.040, 0.060], f32) * max(g - 1.0, 0.0) * 1.8
        out += self.rim[..., None] * np.array([0.05, 0.06, 0.08], f32) * g
        wl = (1.0 + 0.25 * (s["cur"] == "light")) * (1 + 0.025 * math.sin(t * 7.3) + 0.015 * math.sin(t * 13.1))
        out += self.win_rgb * 1.7 * wl
        out += self.spill[..., None] * np.array([1.0, 0.55, 0.22], f32) * 0.05 * wl
        # moonlit snow glints (they multiply when the moonlight brightens)
        tw = np.clip(np.sin(t * self.gfr * 6.283 + self.gph), 0, 1) ** 12 * min(g / 2.5, 1.0)
        if tw.max() > 1e-3:
            lay = np.zeros(self.a.shape, f32); np.add.at(lay, (self.gy, self.gx), tw * 0.9)
            lay = cv2.GaussianBlur(lay, (0, 0), 0.8) * 4 + cv2.GaussianBlur(lay, (0, 0), 2.5) * 1.5
            out += lay[..., None] * np.array([0.85, 0.92, 1.0], f32)
        return out

    # -------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        W, H = self.W, self.H
        s = state(t); S = s["S"]; cur = s["cur"]; t0, t1 = s["t0"], s["t1"]
        cx, cy = s["pos"]
        pulse = 1 + 0.04 * math.sin(2 * math.pi * t / 2.2) + sum(0.18 * math.exp(-((t - tp) / 0.22) ** 2) for tp in PULSES)
        u_in = (t - t0) / 0.55
        g_in = back_out(u_in) if s["prev"] else 1.0
        imp = 0.0 if t1 > 1e8 else ramp(t, t1 - 0.32, t1)                # the old Moon swells, then implodes into the flash
        scale = g_in * (1 + 0.25 * ease(imp / 0.5) if imp < 0.5 else g_in * (1.25 - 1.2 * ease((imp - 0.5) / 0.5)))
        scale = max(scale, 0.03)
        E = s["E"]
        # ---- sky
        sky = self.night * (1 + 0.6 * (s["sky"] - 1))
        st = self.stars.render(self.cam, t, gain=1.0, twinkle=0.8, air=0.6, plate_gain=0.45 / s["sky"], star_gain=1.2 / s["sky"] ** 1.3,
                               rot=0.4 * t / DUR)
        sky = sky + st
        dx, dy = self.xx - cx, self.yy - cy; d = np.sqrt(dx * dx + dy * dy)
        col = self.ext_col(cy)
        aure = np.exp(-np.maximum(d - RP, 0) / 70) * 0.10 + np.exp(-np.maximum(d - RP, 0) / 320) * 0.035
        sky = sky + (aure * E ** 0.7 * pulse)[..., None] * col * np.array([0.85, 0.92, 1.05], f32)
        img = sky.astype(f32)
        # ---- the Moon (+ rings)
        RG.set_sun(sun_vec(s["phase"], s["pa"]))
        I = pulse * (1 - 0.5 * imp)
        if s["rings"]:
            self.moon.set_ring_pole(pole_vec(S["roll"], s["tip"]))
            self.moon.render(img, cx, cy, t, I=I, scale=scale, light=tuple(col))
            if cur == "edge":                                               # the hairline catches the sunlight: a soft glint
                self.edge_glow(img, t, cx, cy, s["tip"], S["roll"], scale)
        else:
            self.moon0.render(img, cx, cy, t, I=I, scale=scale, light=tuple(col))
        # ---- beams: a burst at each swap
        bl = 0.9 * math.exp(-(t - t0) / 1.1) if s["prev"] else 0.0
        if bl > 0.02: img = img + self.beams_layer(t, cx, cy, bl, S["beams"])
        # ---- the village
        fgc = self.relight(t, E, s)
        a = self.a[..., None]
        img = img * (1 - a) + fgc * a
        # ---- flashes and shockwaves
        for ts, k in SWAPS:
            u = t - ts
            if -0.05 < u < 1.5:
                NS = ST[k]; fc = 0.45 + 0.55 * np.array(NS["fl"], f32)
                px, py = (RISE0 if k == "ring" else C)
                fl = math.exp(-max(u, 0) / 0.09) * ease((u + 0.05) / 0.05)
                dd = np.sqrt((self.xx - px) ** 2 + (self.yy - py) ** 2)
                img += (fl * (np.exp(-dd / 260) * 2.6 + 0.30))[..., None] * fc
                R = 2300 * (max(u, 0) / 1.5) ** 0.6; wdt = 16 + 55 * u
                for ch, off in ((0, 12), (1, 0), (2, -12)):
                    img[..., ch] += np.exp(-((dd - R - off) / wdt) ** 2) * 1.3 * math.exp(-max(u, 0) / 0.5)
        if T_WO0 < t < T_GONE + 0.5:
            v = ramp(t, T_WO0, T_GONE) ** 2.2 * (1 - ramp(t, T_GONE, T_GONE + 0.5))
            img = img + (8.0 * v) * np.array([1.0, 0.96, 0.9], f32)
        img = self.chroma_bloom(img, 1.0)
        out = tonemap(img, 1.25)
        out = self.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.14)
        self.overlay(out, t, s)
        return out

    def edge_glow(self, img, t, cx, cy, tip, roll, scale):
        """sunlight glinting along the edge-on ring plane: a soft line hugging the ring, brightest at its ansae"""
        thin = smooth(4.0, 0.5, tip)
        if thin <= 0.01: return
        r = math.radians(roll)
        ux, uy = math.cos(r), math.sin(r)
        dx, dy = self.xx - cx, self.yy - cy
        al = dx * ux + dy * uy; pp = -dx * uy + dy * ux
        Rr = RP * 2.33 * scale
        along = smooth(Rr + 6, Rr - 4, np.abs(al)) * smooth(RP * 0.9, RP * 1.3, np.abs(al))
        line = np.exp(-(pp / 1.1) ** 2) * 0.9 + np.exp(-np.abs(pp) / 7.0) * 0.12
        ans = np.exp(-((np.abs(al) - Rr * 0.75) / (Rr * 0.25)) ** 2)
        img += ((line * along * (0.5 + 0.8 * ans)) * thin * (1 + 0.1 * math.sin(t * 3)))[..., None] * np.array([1.0, 0.95, 0.85], f32)

    def chroma_bloom(self, img, amt):
        img = bloom(img, 0.85 * amt)
        H, W = img.shape[:2]
        sm = cv2.resize(img, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
        sm = np.maximum(sm - 1.0, 0)
        acc = np.empty_like(sm)
        for c, sg in ((0, 26), (1, 20), (2, 15)):
            acc[..., c] = cv2.GaussianBlur(sm[..., c], (0, 0), sg)
        return img + cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR) * 0.30 * amt

    def chroma(self, out):
        W, H = self.W, self.H
        o = out.copy()
        for ch, k in ((0, 1.0016), (2, 0.9984)):
            M = np.float32([[k, 0, (1 - k) * W / 2], [0, k, (1 - k) * H / 2]])
            o[..., ch] = cv2.warpAffine(out[..., ch], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return o

    # -------------------------------------------------------------------------------------------- overlay (sRGB)
    def overlay(self, out, t, s):
        L = self.L; W = L.W
        cur, t0 = s["cur"], s["t0"]
        S = ST[cur]
        x, ys = W / 2, (300, 385, 440)
        a = ramp(t, max(t0, 0.25) + 0.15, max(t0, 0.25) + 0.45)
        if s["t1"] < 1e8: a *= 1 - ramp(t, s["t1"] - 0.35, s["t1"] - 0.15)
        if cur == "end": a = ramp(t, T_GONE + 0.7, T_GONE + 1.0)
        if T_WO0 < t < T_GONE: a = 0.0
        if a > 0.01:
            dy = (1 - a) * 18
            rgba, _ = word_layer(S["name"], int(L.hud_size * 1.4), W * 0.9, fill=S["tc"])
            composite(out, rgba, x, ys[0] + dy, a)
            hud_text(out, S["l2"], x, ys[1] + dy, int(L.hud_size * 0.58), "Black", (255, 255, 255), a, 0.06, display=True)
            hud_text(out, S["l3"], x, ys[2] + dy, int(L.hud_size * 0.46), "Bold", (232, 240, 255), a, 0.08, display=True)
        self.caps.draw(out, t)


def save(im, p): Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p)


if __name__ == "__main__":
    if sys.argv[1] == "info":
        print("DUR", DUR, "RP", round(RP, 2), "ring outer px", round(RP * SC.k_out, 1))
        print({k: round(v, 2) for k, v in T_SW.items()}, "gone", round(T_GONE, 2), "rise1", round(T_RISE1, 2), "edge1", round(T_EDGE1, 2))
        sys.exit()
    if sys.argv[1] == "seg":
        from lib.v3_kit import render; render(sys.modules[__name__]); sys.exit()
    sc = Scene(); os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
    for t in [float(x) for x in sys.argv[2].split(",")]:
        t0 = time.time(); im = sc.frame(t)
        save(im, os.path.join(SCR, "stills", f"vert_{t:05.2f}.png")); print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)
