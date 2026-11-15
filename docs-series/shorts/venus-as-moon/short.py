"""WHAT IF VENUS WERE OUR MOON? -- one locked tripod shot of the suburban backyard (08_suburban_backyard.png) at night,
string lights and the house window on. BATCH4 swap format: each beat swaps in with a tinted flash + chromatic shockwave,
the yard is relit for the new light source, readouts at the top, big orange one-word captions.
  our Moon (0.52 deg) -> Venus at the Moon's distance (1.80 deg): a thin crescent (already brighter than a full Moon)
  -> half (~20x) -> full (~70x: the night lit like dusk; crisp shadows of the fence, shed and trampoline reach towards us)
  -> "under those clouds": 465 C, 92 bar; tides 66x -> white-out -> our Moon again (loops)
Lens: telephoto, f = 9,000 px for the discs (true angular sizes, true ratio 3.48); the yard keeps its own wide lens.
Venus is a procedural cloud deck (no Venus map in shorts-common): creamy, low-contrast zonal bands and streaks, thick
limb haze and a lit atmospheric rim, slowly super-rotating.
Usage (one heavy process, under nice):  /home/user/ttsenv/bin/python short.py info | stills 1.0,9.5 | segs
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401
import numpy as np, cv2
from PIL import Image
from lib.core import f32, Layout, ramp, smooth, ease, fbm2, lum
from lib.foreground import Foreground
from lib.sky import SkyCam, StarSky
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish
from lib.audio import place
import moons as MO
from moons import Body, pole_vec

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B4-venus-as-moon"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/08_suburban_backyard.png"
FPS = 30
LEAD, TAIL = 0.25, 1.40
F_TELE = 9000.0
F_YARD = 771.0                    # the photo's own lens (~70 deg wide) for the shadow geometry
HZ_EYE = 1590.0                   # eye-level horizon in the yard photo (just under the fence top)
EL_LIGHT = math.radians(35.0)     # elevation used for the cast shadows
AZ_LIGHT = math.radians(-6.0)     # light slightly left of straight ahead
F_SKY = 1400.0
VX, VY = 540.0, 720.0
CAP_Y = 1150
RO_Y = (318, 398, 450)

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}


def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]


# ------------------------------------------------------------------------------------------------ science
D_MOON, R_MOON, R_VEN = 384400.0, 1737.4, 6051.8
M_MOON, M_VEN, M_E = 7.342e22, 4.8675e24, 5.9722e24
ANG_MOON = 2 * math.degrees(math.atan(R_MOON / D_MOON)); ANG_VEN = 2 * math.degrees(math.atan(R_VEN / D_MOON))
RP_MOON = F_TELE * R_MOON / D_MOON; RP_VEN = F_TELE * R_VEN / D_MOON
P_GEO_VEN, P_GEO_MOON = 0.689, 0.12                                      # geometric albedos


def venus_mag(alpha_deg, delta_au=D_MOON / 1.495978707e8, r_au=1.0):
    """Mallama (2006) Venus phase curve, V(1, a) for a < 163.7 deg"""
    a = alpha_deg
    v1 = -4.384 - 1.044e-3 * a + 3.687e-4 * a ** 2 - 2.814e-6 * a ** 3 + 8.938e-9 * a ** 4
    return v1 + 5 * math.log10(r_au * delta_au)


V_FULL_MOON = -12.74
def x_moon(alpha): return 10 ** (-0.4 * (venus_mag(alpha) - V_FULL_MOON))   # Venus light / full-Moon light
TIDE = (M_VEN / M_MOON)                                                      # same distance: tidal acceleration ratio
BARY = D_MOON * M_VEN / (M_VEN + M_E)                                        # km from Earth's centre
P_ORB = 27.32 * math.sqrt((M_E + M_MOON) / (M_E + M_VEN))                    # days (sidereal)

# ------------------------------------------------------------------------------------------------ stages
# alpha: phase angle (deg); key: light on the yard (direct, shadows); amb: sky / ambient; sky: sky brightening
SUN_DIR = np.array([-0.30, 0.95]); SUN_DIR = SUN_DIR / np.linalg.norm(SUN_DIR)   # the (set) Sun is below, a little left
STAGES = {
    "moon": dict(body="moon", alpha=4.0, name="OUR MOON", l2="0.52° WIDE", l3="384,400 KM AWAY", tc=(235, 240, 255),
                 key=0.10, amb=0.06, sky=0.0, glow=(0.62, 0.70, 0.95), fl=(0.85, 0.9, 1.0)),
    "cres": dict(body="ven", alpha=135.0, name="VENUS · CRESCENT", l2="1.8° WIDE · 3.5× THE MOON", l3="~6× THE LIGHT OF A FULL MOON",
                 tc=(255, 236, 190), key=0.20, amb=0.09, sky=0.15, glow=(1.0, 0.92, 0.72), fl=(1.0, 0.95, 0.8)),
    "half": dict(body="ven", alpha=90.0, name="VENUS · HALF", l2="~20× A FULL MOON", l3="ITS CLOUDS REFLECT 76% OF SUNLIGHT",
                 tc=(255, 225, 160), key=0.34, amb=0.14, sky=0.35, glow=(1.0, 0.90, 0.70), fl=(1.0, 0.92, 0.7)),
    "full": dict(body="ven", alpha=4.0, name="FULL VENUS", l2="~70× A FULL MOON · MAG −17", l3="~17 LUX: LIKE DUSK",
                 tc=(255, 245, 215), key=0.80, amb=0.30, sky=1.0, glow=(1.0, 0.93, 0.78), fl=(1.0, 0.97, 0.88)),
    "hell": dict(body="ven", alpha=4.0, name="UNINHABITABLE", l2="SURFACE 465 °C · 92× OUR AIR PRESSURE", l3="TIDES 66× THE MOON'S",
                 tc=(255, 150, 80), key=0.80, amb=0.30, sky=1.0, glow=(1.0, 0.75, 0.50), fl=(1.0, 0.7, 0.45)),
}
STAGES["end"] = STAGES["moon"]
T_SW = {"cres": LN["ven"]["start"] - 0.06, "half": LN["half"]["start"] - 0.06, "full": wt("full", "FULL") - 0.08,
        "hell": LN["hell"]["start"] - 0.06}
T_BACK = LN["end"]["start"] - 0.10
T_WO0 = T_BACK - 0.80
SWAPS = [(T_SW[k], k) for k in ("cres", "half", "full", "hell")] + [(T_BACK, "end")]
T_SHADOW = wt("full_c", "SHADOWS") - 0.3
PULSES = [wt("hook", "VENUS"), wt("moon", "SMALL"), wt("ven", "VENUS"), wt("ven_b", "WIDER"), wt("cres", "OUTSHINES"), wt("half", "20×"),
          wt("full", "FULL"), wt("full_b", "70"), wt("full_c", "DUSK"), wt("full_c", "SHADOWS"), wt("hell", "MELT"), wt("hell_b", "SWAMP"),
          wt("end_b", "PERFECT")]


def stage_at(t):
    cur, t0 = "moon", -10.0
    for ts, k in SWAPS:
        if t >= ts: cur, t0 = k, ts
    nxt = [ts for ts, k in SWAPS if ts > t]
    return cur, t0, (nxt[0] if nxt else 1e9)


def lerp(a, b, w): return tuple(x + (y - x) * w for x, y in zip(a, b)) if isinstance(a, tuple) else a + (b - a) * w


def back_out(u, s=2.2):
    u = min(max(u, 0.0), 1.0) - 1; return 1 + u * u * ((s + 1) * u + s)


def sun_vec(alpha):
    a = math.radians(alpha)
    return [math.sin(a) * SUN_DIR[0], math.sin(a) * SUN_DIR[1], -math.cos(a)]


# ------------------------------------------------------------------------------------------------ Venus cloud map
def venus_tex():
    """procedural cloud deck (equirectangular): creamy white-yellow, low contrast; zonal bands, sheared streaks and a
    faint dark 'Y' (the UV feature, kept very subtle as Venus is nearly featureless in visible light)"""
    p = os.path.join(SCR, "venus_proc.png")
    if os.path.exists(p): return p
    h, w = 1024, 2048
    lat = np.linspace(90, -90, h)[:, None] * np.ones((1, w)); lon = np.linspace(-180, 180, w)[None, :] * np.ones((h, 1))
    n1 = fbm2((h, w), 501, 2.6); n2 = fbm2((h, w), 502, 1.9)
    st = cv2.GaussianBlur(n2, (0, 0), sigmaX=22, sigmaY=1.6); st /= st.std() + 1e-6           # zonal streaks
    sh = cv2.GaussianBlur(n1, (0, 0), sigmaX=4, sigmaY=3); sh /= sh.std() + 1e-6
    bands = np.sin(np.radians(lat) * 9 + 0.8 * sh) * np.cos(np.radians(lat)) ** 0.5
    y_arm = np.exp(-((lat - 0.35 * np.abs(lon + 30) * np.sign(lat + 1e-3) * 0.6) / 9) ** 2) * np.exp(-((lon + 30) / 80) ** 2)
    g = 1 + 0.06 * bands + 0.025 * st + 0.035 * sh - 0.09 * y_arm
    g = g * (1 - 0.06 * (np.abs(lat) / 90) ** 3) + 0.03 * np.exp(-((np.abs(lat) - 62) / 6) ** 2)  # bright polar collars
    col = np.clip(g, 0.8, 1.15)[..., None] * np.array([0.98, 0.92, 0.78])
    Image.fromarray((np.clip(col * 0.86, 0, 1) * 255).astype(np.uint8)).save(p)
    return p


def prep_norm(t): return t / max(float(lum(t).mean()), 1e-4)


# ------------------------------------------------------------------------------------------------ scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(True); W, H = L.W, L.H
        self.fg = fg = Foreground(FG_PATH, L, hz_frac=0.97)
        self.hz = fg.horizon
        self.cam = SkyCam(W, H, 1590.0, F_SKY)
        self.stars = StarSky()
        hw, hh = W // 2, H // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.hx, self.hy = xx, yy
        e = np.maximum(np.degrees(np.arctan2(1590.0 - yy, F_SKY)), 0).astype(f32)
        self.night = (np.array([0.006, 0.012, 0.045], f32) * (0.8 + 0.2 * np.exp(-e / 25))[..., None]
                      + np.array([0.020, 0.018, 0.030], f32) * np.exp(-e / 7)[..., None]).astype(f32)      # + suburban light dome
        k = np.exp(-e / 22)[..., None]
        self.dusk = (np.array([0.012, 0.045, 0.22], f32) * (1 - k) + np.array([0.10, 0.10, 0.24], f32) * k
                     + np.array([0.14, 0.06, 0.04], f32) * np.exp(-e / 4)[..., None]).astype(f32)
        yy2, xx2 = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xx2, yy2
        MO.set_sun(sun_vec(4.0))
        self.moon = Body("moon", "8k_moon.jpg", RP_MOON, pole_vec(-12, 4), model="rock", surf=1.15, detail=0.0, prep=prep_norm)
        self.ven = Body("ven", venus_tex(), RP_VEN, pole_vec(-8, 6), model="giant", k=0.80, surf=1.7,
                        haze=(0.55, 0.45, 0.30), rim=(1.6, 1.35, 1.0), winds=0.02, spin=0.03, detail=0.01, prep=prep_norm, seed=9, night=0.012)
        # ---- yard: lights / window, base, albedo, rim (as andromeda-collision)
        a = fg.a; rgb = fg.rgb; f = fg.flat; y = lum(f)[..., None]
        mxc = rgb.max(2); warm = rgb[..., 0] - rgb[..., 2]
        win = (smooth(0.30, 0.75, mxc) * smooth(0.05, 0.20, warm) * (yy2 > 1300)).astype(f32)
        self.lights = (rgb * win[..., None] * 3.0 + win[..., None] * np.array([0.30, 0.14, 0.03], f32)).astype(f32)
        glow = cv2.GaussianBlur(win, (0, 0), 6) * 0.5 + cv2.GaussianBlur(win, (0, 0), 25) * 0.6
        self.lglow = (glow[..., None] * np.array([1.0, 0.55, 0.20], f32) * 0.35).astype(f32)
        self.alb = np.clip(f * 0.8 + y * 0.2, 0, 1).astype(f32) * (1 - win[..., None])
        self.base = (self.alb * np.array([0.30, 0.36, 0.75], f32) * 0.10).astype(f32)
        sh = np.zeros_like(a); sh[6:] = a[:-6]
        self.rim = (cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 2.0) * a)[..., None].astype(f32)
        self.lawn, self.shadow = self._shadows()
        self.caps = Captions(L, WORDS, emphasis={"VENUS", "MOON", "SMALL", "WIDER", "CRESCENT", "OUTSHINES", "HALF", "20×", "FULL", "70",
                                                  "DUSK", "SHADOWS", "CLOUDS", "MELT", "LEAD", "TIDES", "SWAMP", "PERFECT"})
        L.cap_y = CAP_Y

    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    # -------------------------------------------------------------------------------------------- cast shadows
    def _shadows(self):
        """lawn mask + shadow mask for a light ahead of us (elevation 35 deg, slightly left): every caster pixel (fence,
        shed, plants, trampoline mat / frame / poles; the net mesh at 25 %) is lifted off its ground point and thrown
        along the ground towards the camera with the yard photo's perspective"""
        p = os.path.join(SCR, "shadow.npz")
        if os.path.exists(p):
            z = np.load(p); return z["lawn"], z["shadow"]
        fg = self.fg; a = fg.a; rgb = fg.rgb; H, W = a.shape
        xx, yy = self.xx, self.yy
        g = rgb[..., 1]; r = rgb[..., 0]; b = rgb[..., 2]
        lawn = ((g > r * 1.08) & (g > b * 1.15) & (yy > 1738) & (a > 0.9)).astype(np.uint8)
        patio = np.zeros((H, W), np.uint8)
        cv2.fillPoly(patio, [np.array([(890, 1740), (1080, 1740), (1080, 1919), (790, 1919)], np.int32)], 1)
        lawn = cv2.morphologyEx(lawn * (1 - patio), cv2.MORPH_CLOSE, np.ones((41, 41), np.uint8)) * (1 - patio) * (a > 0.9)
        lawn = cv2.GaussianBlur(lawn.astype(f32), (0, 0), 1.0)
        # casters and their ground lines
        tramp = (xx > 70) & (xx < 370) & (yy > 1550) & (yy < 1810)
        mat = tramp & (b > r * 1.25) & (yy > 1700) & (yy < 1750)
        fence = (a > 0.6) & (yy > 1548) & (yy < 1738) & (xx < 885) & ~tramp
        w = np.zeros((H, W), f32); base = np.zeros((H, W), f32)
        w[fence] = 1.0; base[fence] = 1736.0
        net = tramp & (a > 0.6) & ~mat & (yy < 1712)
        w[net] = 0.25; base[net] = 1798.0
        w[mat] = 1.0; base[mat] = 1798.0 - (1798 - 1727) * 0.0
        ys, xs = np.nonzero(w > 0)
        ws = w[ys, xs]; yb = base[ys, xs]
        if True:   # the mat sits ~0.9 m up: its pixels are at their own height above the feet line
            pass
        pts = [(xs.astype(f32), ys.astype(f32), yb, ws)]
        # the trampoline's frame legs and net poles (thin lines): top -> foot
        for x0, y0, x1, y1, base_y in ((85, 1560, 85, 1795, 1798), (118, 1560, 112, 1800, 1800), (320, 1560, 322, 1790, 1792),
                                       (355, 1600, 357, 1780, 1782), (232, 1735, 232, 1805, 1805)):
            n = 260; u = np.linspace(0, 1, n, dtype=f32)
            for dx in (-1.5, -0.5, 0.5, 1.5):
                pts.append(((x0 + (x1 - x0) * u + dx).astype(f32), (y0 + (y1 - y0) * u).astype(f32), np.full(n, base_y, f32), np.full(n, 1.0, f32)))
        X_ = np.concatenate([q[0] for q in pts]); Y_ = np.concatenate([q[1] for q in pts]); B_ = np.concatenate([q[2] for q in pts])
        Wt = np.concatenate([q[3] for q in pts])
        Z = F_YARD / np.maximum(B_ - HZ_EYE, 1.0)                           # camera height = 1 unit
        X = (X_ - 540) * Z / F_YARD
        h = np.maximum(B_ - Y_, 0) * Z / F_YARD
        D = h / math.tan(EL_LIGHT)
        Xs = X - D * math.sin(AZ_LIGHT); Zs = Z - D * math.cos(AZ_LIGHT)
        ok = Zs > 0.3
        xs_ = 540 + F_YARD * Xs[ok] / Zs[ok]; ys_ = HZ_EYE + F_YARD / Zs[ok]; Wt = Wt[ok]
        sel = (xs_ >= 0) & (xs_ < W - 1) & (ys_ >= 0) & (ys_ < H - 1)
        acc = np.zeros((H, W), f32)
        np.maximum.at(acc, (ys_[sel].astype(int), xs_[sel].astype(int)), Wt[sel])
        acc = cv2.morphologyEx(acc, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        acc = cv2.GaussianBlur(acc, (0, 0), 1.3)                            # 1.8 deg source: a narrow penumbra
        shadow = np.clip(acc, 0, 1).astype(f32)
        np.savez_compressed(p, lawn=lawn.astype(f32), shadow=shadow)
        return lawn.astype(f32), shadow

    # -------------------------------------------------------------------------------------------- sky
    def sky(self, t, S0, S1, w, cx, cy, Rp, bright):
        sk = lerp(S0["sky"], S1["sky"], w)
        base = self.night + (self.dusk - self.night) * min(sk, 1.0)
        g = np.array(lerp(S0["glow"], S1["glow"], w), f32)
        d = np.sqrt((self.hx - cx) ** 2 + (self.hy - cy) ** 2); dd = np.maximum(d - Rp, 0)
        aure = (np.exp(-dd / (25 + 0.4 * Rp)) * 0.35 + np.exp(-dd / (160 + 1.2 * Rp)) * 0.08 + np.exp(-dd / 700) * 0.03) * bright
        return base + aure[..., None] * g, aure

    def shock(self, img, cx, cy, u, col, size=1.0, decay=0.55):
        R = 2400 * size * (max(u, 0) / 1.4) ** 0.6; wdt = (18 + 60 * u) * size
        dd = np.sqrt((self.xx - cx) ** 2 + (self.yy - cy) ** 2)
        for ch, off in ((0, 10), (1, 0), (2, -10)):
            img[..., ch] += np.exp(-((dd - R - off * size) / wdt) ** 2) * 2.0 * math.exp(-max(u, 0) / decay) * (0.6 + 0.4 * col[ch])

    # -------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        cur, t0, t1 = stage_at(t)
        S = STAGES[cur]
        prev = [k for ts, k in SWAPS if ts < t0]
        A = STAGES[prev[-1]] if prev else STAGES["moon"]
        w = ramp(t, t0 - 0.10, t0 + 0.6) if t0 > 0 else 1.0
        pulse = 1 + 0.04 * math.sin(2 * math.pi * t / 1.7) + sum(0.25 * math.exp(-((t - tp) / 0.2) ** 2) for tp in PULSES)
        body = self.moon if S["body"] == "moon" else self.ven
        Rp = RP_MOON if S["body"] == "moon" else RP_VEN
        # bloom-in on a body change, swell + implode before one
        sc = 1.0
        if t0 > 0 and A["body"] != S["body"]: sc = back_out((t - t0) / 0.65) if t > t0 else 0.0
        nxt = [(ts, k) for ts, k in SWAPS if ts > t]
        if nxt and STAGES[nxt[0][1]]["body"] != S["body"]:
            cu = max(0.0, 1 - (nxt[0][0] - t) / 0.42)
            if cu > 0: sc *= (1 + 0.3 * ease(cu / 0.45)) if cu < 0.45 else 1.3 * (1 - ease((cu - 0.45) / 0.55) ** 0.7) + 0.02
        # phase light: the Venus light factor (x full Moon) drives the sky + yard; compressed for the screen
        alpha = S["alpha"]
        bright = (0.6 + 0.4 * pulse) * (1.0 if S["body"] == "moon" else 0.35 + 0.95 * min(x_moon(alpha) / 70, 1))
        off = Rp * 0.55 * math.sin(math.radians(alpha))                      # the glow sits on the lit limb
        sky, aure = self.sky(t, A, S, w, VX + off * SUN_DIR[0], VY + off * SUN_DIR[1], Rp * max(sc, 0.05) * (1 - 0.4 * math.sin(math.radians(alpha))), bright)
        img = self.up(sky)
        sk = lerp(A["sky"], S["sky"], w)
        st = self.stars.render(self.cam, t, gain=1.0, twinkle=1.2, plate_gain=0.12, star_gain=1.0, cx=1800, cy=900, rot=4.0)
        img += st * (np.exp(-self.up(aure) * 4) * (1 - 0.85 * min(sk, 1)))[..., None] * 0.9
        MO.set_sun(sun_vec(alpha))
        if sc > 0.01:
            body.render(img, VX, VY, t, I=pulse, scale=sc)
        # ---- the yard: night base + ambient + direct (shadowed, on the lawn) + rim + lights
        key = lerp(A["key"], S["key"], w) * (1 + 0.1 * (pulse - 1)); amb = lerp(A["amb"], S["amb"], w)
        gcol = np.array(lerp(A["glow"], S["glow"], w), f32)
        shad = self.shadow * smooth(0.0, 0.25, key) if True else 0
        direct = (self.lawn * (1 - 0.93 * shad))[..., None] * gcol * key * 0.9
        ambient = self.alb * (np.array([0.45, 0.55, 0.85], f32) * amb * 0.5)
        yard = self.base + ambient + self.alb * direct + self.rim * gcol * key * 0.2
        yard = yard + self.lights + self.lglow
        a = self.fg.a[..., None]
        img = img * (1 - a) + yard * a + self.lglow * (1 - a) * 0.5
        # ---- swap flashes + chromatic shockwaves
        for ts, k in SWAPS:
            u = t - ts
            if -0.05 < u < 1.4 and k != "end":
                fc = np.array(STAGES[k]["fl"], f32)
                img += (2.6 * math.exp(-max(u, 0) / 0.08) * ease((u + 0.05) / 0.05)) * fc
                self.shock(img, VX, VY, u, fc)
        if T_WO0 < t < T_BACK:
            v = ease((t - T_WO0) / (T_BACK - T_WO0)); img = img + (30 * v ** 2.5) * np.array([1.0, 0.97, 0.92], f32)
        if T_BACK <= t < T_BACK + 0.6:
            img = img + 30 * math.exp(-(t - T_BACK) / 0.10) * np.array([0.95, 0.95, 1.0], f32)
            self.shock(img, VX, VY, t - T_BACK, np.array([0.85, 0.9, 1.0], f32))
        img = bloom(img, 0.9)
        out = tonemap(img, 1.0)
        out = finish(out, t, grain=0.008, vignette=0.14)
        self.overlay(out, t, cur, t0)
        return out

    def overlay(self, out, t, cur, t0):
        L = self.L; W = L.W; S = STAGES[cur]
        x = W / 2; ys = RO_Y
        start = LN["moon"]["start"] if cur == "moon" else (LN["end"]["start"] if cur == "end" else t0)
        a = ramp(t, start + 0.15, start + 0.45)
        nxt = [ts for ts, k in SWAPS if ts > t]
        if nxt: a *= 1 - ramp(t, nxt[0] - 0.35, nxt[0] - 0.15)
        if T_WO0 < t < T_BACK: a = 0.0
        if cur == "end": a *= 1 - ramp(t, DUR - 0.9, DUR - 0.4)
        if a > 0.01:
            dy = (1 - a) * 18
            big = int(L.hud_size * (1.35 if len(S["name"]) < 13 else 1.12))
            rgba, _ = word_layer(S["name"], big, W * 0.9, fill=S["tc"])
            composite(out, rgba, x, ys[0] + dy, a)
            hud_text(out, S["l2"], x, ys[1] + dy, int(L.hud_size * 0.58), "Black", (255, 255, 255), a, 0.08, display=True)
            hud_text(out, S["l3"], x, ys[2] + dy, int(L.hud_size * 0.46), "Bold", (240, 242, 250), a, 0.10, display=True)
        self.caps.draw(out, t)


def run_stills(ts):
    sc = Scene(); os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
    for t in ts:
        t0 = time.time(); im = sc.frame(t)
        Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(SCR, "stills", f"{t:05.2f}.png"))
        print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "info":
        print("DUR", DUR, f"Moon {ANG_MOON:.3f} deg r {RP_MOON:.1f} px | Venus {ANG_VEN:.3f} deg r {RP_VEN:.1f} px | ratio {R_VEN / R_MOON:.2f}")
        for al in (135, 90, 4, 0.0001): print(f"alpha {al:6.1f}: V = {venus_mag(al):6.2f}  = {x_moon(al):5.1f} x full Moon  ~{x_moon(al) * 0.25:5.1f} lux")
        print(f"tides x{TIDE:.1f}; barycentre {BARY:,.0f} km from Earth's centre; orbit {P_ORB:.1f} d")
        print("swaps", [(round(a, 2), k) for a, k in SWAPS]); sys.exit()
    if sys.argv[1] == "segs":
        from lib.v3_redo_q5 import render_segments
        render_segments(sys.modules[__name__]); sys.exit()
    if sys.argv[1] == "stills":
        run_stills([float(x) for x in sys.argv[2].split(",")])
