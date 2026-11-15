"""WHAT IF A ROGUE PLANET PASSED EARTH? -- one locked tripod shot of the wet city street at night
(04_city_street_at_night.png). The sky is a narrow strip between the skyscrapers; the plate's lens is ~f = 1150 px, and the
planet is drawn at its TRUE angular size at every distance (science.py), overflowing behind the buildings when close:
  normal night -> beyond Neptune (3.9", a star blinks out) -> Mars's distance (0.14 deg, a dark speck)
  -> the Moon's distance (21 deg: a dark disc blotting out the stars, a thin sunlit crescent, a faint red glow from its own
     heat, lightning in its clouds, auroral ovals, star images squeezed along its limb by atmospheric refraction)
  -> closer, 200,000 km (42 deg: tides, quakes, the city lights flicker) -> the flyby (it slides away and shrinks)
  -> white-out -> the normal city night (loops)
Every swap: a tinted flash + chromatic shockwave + beams; the city is relit (planet glow, lightning), and the wet street
mirrors the sky (streaky rough-specular reflection) on top of the plate's own neon reflections.
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py info | stills 1.0,9.5 | segs
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401
import numpy as np, cv2
from PIL import Image
from lib.core import f32, Layout, ramp, smooth, ease, fbm2, lum, splat, noise1, bbcolor
from lib.foreground import Foreground
from lib.sky import SkyCam, StarSky
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish
from lib.audio import place
import moons as MO
from moons import Body, pole_vec
import science as SC

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B3-rogue-planet"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/04_city_street_at_night.png"
FPS = 30
LEAD, TAIL = 0.25, 1.40
F = SC.F_PX
YH = 1366.0                        # eye level (the street's vanishing point), frame px
CAP_Y = 1150
RO_Y = (318, 398, 450)
PC = (552.0, 700.0)                # planet centre in the sky strip

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}


def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]


# the planet is lit by the Sun from below the horizon, behind it (phase angle ~140 deg): a thin crescent at the bottom
PHASE = math.radians(140)
MO.set_sun([0.30 * math.sin(PHASE), 0.95 * math.sin(PHASE), -math.cos(PHASE)])
R_MOON_PX = SC.rad_px(SC.DIST["moon"]); R_CLOSE_PX = SC.rad_px(SC.DIST["close"])
R_MARS_PX = SC.rad_px(SC.DIST["mars"])

SET = {
    "night": dict(name="", l2="", l3="", tc=(235, 240, 255), glow=(0.55, 0.45, 0.85), gl=0.0,
                  beams=[(0.50, 0.40, 1.0), (0.30, 0.80, 1.0), (0.95, 0.35, 0.80)], bI=0.06, tint=(0.0, 0.0, 0.0), red=0.0, stars=1.0),
    "hook": dict(name="ROGUE PLANET", l2="1 JUPITER MASS · NO STAR", l3="DRIFTING BETWEEN THE STARS", tc=(255, 150, 120),
                 glow=(0.55, 0.45, 0.85), gl=0.0, beams=[(0.70, 0.30, 1.0), (1.0, 0.30, 0.40), (0.30, 0.70, 1.0)], bI=0.10,
                 tint=(0, 0, 0), red=0.0, stars=1.0),
    "nep": dict(name="BEYOND NEPTUNE", l2="50 AU AWAY · 4 ARCSECONDS", l3="TOO FAINT TO SEE", tc=(150, 200, 255),
                glow=(0.40, 0.60, 1.0), gl=0.0, beams=[(0.35, 0.60, 1.0), (0.45, 0.95, 1.0), (0.70, 0.45, 1.0)], bI=0.10,
                tint=(0, 0, 0), red=0.0, stars=1.15),
    "mars": dict(name="MARS'S DISTANCE", l2="56 MILLION KM · 0.14° WIDE", l3="A DARK SPECK", tc=(255, 160, 110),
                 glow=(1.0, 0.45, 0.30), gl=0.0, beams=[(1.0, 0.40, 0.25), (0.90, 0.30, 0.60), (0.40, 0.55, 1.0)], bI=0.11,
                 tint=(0, 0, 0), red=0.05, stars=1.15),
    "moon": dict(name="THE MOON'S DISTANCE", l2="21° WIDE · 40 MOONS ACROSS", l3="TIDAL PULL: 26,000× THE MOON'S", tc=(255, 120, 90),
                 glow=(1.0, 0.30, 0.18), gl=1.0, beams=[(1.0, 0.25, 0.15), (0.75, 0.20, 0.90), (0.30, 0.90, 0.75), (1.0, 0.55, 0.20)],
                 bI=0.20, tint=(1.0, 0.35, 0.25), red=0.55, stars=1.0),
    "close": dict(name="200,000 KM", l2="42° WIDE · 80 MOONS ACROSS", l3="TIDAL PULL: 180,000× THE MOON'S", tc=(255, 95, 70),
                  glow=(1.0, 0.25, 0.12), gl=1.4, beams=[(1.0, 0.20, 0.10), (0.85, 0.20, 1.0), (1.0, 0.60, 0.20), (0.35, 0.95, 0.80)],
                  bI=0.28, tint=(1.0, 0.30, 0.20), red=1.0, stars=1.0),
    "odds": dict(name="ROGUE PLANETS", l2="MAYBE ~20 FOR EVERY STAR", l3="THIS CLOSE: ~ONCE IN 10²¹ YEARS", tc=(200, 210, 255),
                 glow=(0.55, 0.45, 0.85), gl=0.0, beams=[(0.50, 0.40, 1.0), (0.30, 0.80, 1.0), (0.95, 0.35, 0.80)], bI=0.08,
                 tint=(0, 0, 0), red=0.0, stars=1.0),
}
FLYBY = dict(name="THE FLYBY", l2="ITS PULL: 500× THE SUN'S", l3="EARTH'S ORBIT COULD BE THROWN OFF", tc=(255, 120, 90))

# ------------------------------------------------------------------------------------------------ timeline
T_SW = {"hook": wt("hook_b", "JUPITER") - 0.08, "nep": wt("nep", "NEPTUNE") - 0.08, "mars": wt("mars", "MARS'S") - 0.08,
        "moon": wt("moon", "MOON'S") - 0.08, "close": wt("close", "CLOSER") - 0.06}
T_BLINK = wt("nep", "BLINKING")
T_PASS0 = LN["pass"]["start"] - 0.05; T_PASS1 = LN["pass_b"]["end"] - 0.2      # the flyby: slides away, shrinks
T_BACK = LN["odds"]["start"] - 0.10                                          # white-out peak -> the normal night
T_WO0 = T_BACK - 0.70
SWAPS = [(T_SW[k], k) for k in ("hook", "nep", "mars", "moon", "close")] + [(T_BACK, "odds")]
COLLAPSE, BLOOM = 0.42, 0.70
T_LIT0 = wt("moon_c", "LIGHTNING") - 0.6
T_QUAKE0, T_QUAKE1 = wt("close_b", "HEAVE") - 0.3, LN["close_b"]["end"] + 0.9
T_END_BLINK = wt("end", "DRIFTING")
PULSES = [wt("hook", "ROGUE"), wt("hook_b", "STAR"), T_BLINK, wt("mars", "SPECK"), wt("moon_b", "FORTY"), wt("moon_c", "LIGHTNING"),
          wt("close_b", "HEAVE"), wt("close_b", "SHAKES"), wt("pass_b", "THROWN"), wt("odds_b", "OUTNUMBER"), T_END_BLINK]


def set_at(t):
    cur, t0 = "night", -10.0
    for ts, k in SWAPS:
        if t >= ts: cur, t0 = k, ts
    nxt = [ts for ts, k in SWAPS if ts > t]
    return cur, t0, (nxt[0] if nxt else 1e9)


def prev_of(k):
    ks = ["night"] + [k_ for _, k_ in SWAPS]
    i = ks.index(k); return ks[i - 1] if i > 0 else None


def back_out(u, s=2.2):
    u = min(max(u, 0.0), 1.0) - 1; return 1 + u * u * ((s + 1) * u + s)


def lerp(a, b, w): return tuple(x + (y - x) * w for x, y in zip(a, b)) if isinstance(a, tuple) else a + (b - a) * w


def pal_list(cols, x):
    C = np.array(cols + [cols[0]], f32); n = len(cols)
    p = (x % 1.0) * n; i = np.floor(p).astype(np.int32); fr = (p - i)[..., None]
    return C[i] * (1 - fr) + C[i + 1] * fr


def planet_state(t, cur, t0):
    """-> (cx, cy, R px, kind) of the planet; kind in none / dot / speck / disc"""
    if cur in ("night", "hook", "odds"): return None
    if cur == "nep":
        return (640.0, 560.0 + 6 * (t - t0), 0.0, "dot")
    if cur == "mars":
        return (470.0 + 9 * (t - t0), 560.0 - 3 * (t - t0), R_MARS_PX, "speck")
    if cur == "moon":
        drift = (t - t0) * 2.0
        return (PC[0] - 10 + drift, PC[1] - 4 + drift * 0.3, R_MOON_PX, "disc")
    # close + the flyby: it slides up and away to the upper right, shrinking as it recedes
    u = ramp(t, T_PASS0, T_PASS1)
    d = SC.DIST["close"] * (1 + 9 * u ** 1.6)                                # receding: true size at every distance
    R = SC.F_PX * math.tan(math.asin(SC.R_J / SC.d_obs(d)))
    x = PC[0] + 3 * (t - t0) + 620 * u ** 1.3; y = PC[1] + 30 - 900 * u ** 1.2
    return (x, y, R, "disc")


# ------------------------------------------------------------------------------------------------ scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(True); W, H = L.W, L.H
        self.fg = fg = Foreground(FG_PATH, L, hz_frac=0.84)
        self.cam = SkyCam(W, H, YH, F)
        self.stars = StarSky()
        hw, hh = W // 2, H // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.hx, self.hy = xx, yy
        e = np.maximum(np.degrees(np.arctan2(YH - yy, F)), 0).astype(f32)
        zen = np.array([0.006, 0.009, 0.034], f32)
        sky = zen * (0.75 + 0.25 * np.exp(-e / 30))[..., None]
        sky += np.array([0.050, 0.026, 0.020], f32) * np.exp(-e / 10)[..., None]        # sodium / LED skyglow low down
        sky += np.array([0.020, 0.012, 0.040], f32) * np.exp(-e / 22)[..., None]        # violet city glow
        self.base_sky = sky.astype(f32)
        yy2, xx2 = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xx2, yy2
        r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 7 + r.uniform(-0.25, 0.25), w=r.uniform(0.14, 0.24), I=r.uniform(0.8, 1.2), hue=r.uniform(0, 1),
                           ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(7)]

        def prep_rogue(t):
            """a young, hot, nearly cloud-free giant: very dark (geometric albedo ~0.05), faintly banded"""
            y = lum(t); y = y / max(float(y.mean()), 1e-4)
            col = np.array([0.55, 0.42, 0.38], f32)
            return (col * (0.6 + 0.4 * y)[..., None]).astype(f32)
        self.pl = {
            "moon": Body("rog", "8k_jupiter.jpg", R_MOON_PX, pole_vec(-18, 14), q=0.935, model="giant", k=0.80, surf=0.40, nightside=0.0, winds=0.010,
                         haze=(0, 0, 0), rim=(0.10, 0.05, 0.04), detail=0.04, prep=prep_rogue, seed=3),
            "close": Body("rog2", "8k_jupiter.jpg", R_CLOSE_PX, pole_vec(-18, 14), q=0.935, model="giant", k=0.80, surf=0.40, nightside=0.0, winds=0.010,
                          haze=(0, 0, 0), rim=(0.10, 0.05, 0.04), detail=0.04, ss=1, prep=prep_rogue, seed=3),
        }
        # thermal-glow map: the belts (dark in reflected light) are where the deeper, hotter layers show (as at 5 microns on Jupiter)
        jt = np.asarray(Image.open(os.path.join(MO.TEX, "8k_jupiter.jpg")).convert("L").resize((1024, 512), Image.LANCZOS), f32) / 255
        jt = jt / jt.mean()
        self.glow_map = np.clip(1.6 - jt, 0.2, 2.0).astype(f32)
        self.cloud_map = np.clip(jt, 0.3, 1.8).astype(f32)                       # bright zones / dark belts (turbulent edges)
        self.pole = MO.frame_of(pole_vec(-18, 14))[1]
        # lightning schedule: Poisson flashes on the night side, clustered in belts
        rr = np.random.default_rng(17); ev = []; t = T_LIT0
        while t < T_PASS1:
            rate = 3.0 if t < T_SW["close"] else 5.0
            t += rr.exponential(1 / rate)
            ang = rr.uniform(0, 2 * np.pi); rad = math.sqrt(rr.uniform(0.0, 0.85))
            lat_band = rr.choice([-0.35, -0.12, 0.18, 0.42]) + rr.normal(0, 0.04)
            ev.append(dict(t=t, u=rad * math.cos(ang) * 0.95, v=lat_band, dur=rr.uniform(0.10, 0.28), I=rr.uniform(0.6, 1.4),
                           n=int(rr.integers(1, 4))))
        self.lightning = ev
        # foreground: emissive lights (windows, neon, lamps and their wet reflections) for flicker; relight fields
        a = fg.a
        Y = lum(fg.rgb)
        self.em = (fg.rgb * smooth(0.22, 0.75, Y)[..., None]).astype(f32)
        self.cell = fbm2((64, 64), 9, 0.0)                                            # per-block flicker phases
        sh = np.zeros_like(a); sh[12:] = a[:-12]
        self.rim = cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 4.0) * a
        self.up_w = (np.clip(1 - yy2 / 1300, 0, 1) ** 0.8 * a).astype(f32)                 # upper facades see the sky
        # wet street: everything below eye level that is ground (not the parked cars / planters); glossiness from the plate
        wet = smooth(YH + 20, YH + 90, yy2)
        cars = ((xx2 > 655) & (yy2 < 1455)) | ((xx2 < 380) & (yy2 < 1465))
        hp = Y - cv2.GaussianBlur(Y, (0, 0), 3)
        gloss = np.clip(0.35 + 4 * np.abs(hp), 0, 1)
        self.wet = (wet * (1 - cars * 0.9) * gloss * a).astype(f32)
        self.caps = Captions(L, WORDS, emphasis={"ROGUE", "PLANET", "JUPITER", "STAR", "NEPTUNE", "BLINKING", "MARS'S", "SPECK",
                                                  "MOON'S", "DARK", "FORTY", "LIGHTNING", "CLOSER", "HEAVE", "SHAKES", "THROWN",
                                                  "TINY", "OUTNUMBER", "STARS", "DRIFTING", "EARTH"})
        L.cap_y = CAP_Y

    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    def mix_params(self, t):
        cur, t0, t1 = set_at(t)
        prev = prev_of(cur) if t0 > 0 else None
        w = ramp(t, t0 - 0.12, t0 + 0.55) if prev else 1.0
        A = SET[prev] if prev else SET[cur]; B = SET[cur]
        return A, B, w, cur, t0, t1

    def quake(self, t): return ramp(t, T_QUAKE0, T_QUAKE0 + 0.5) * (1 - ramp(t, T_QUAKE1 - 0.8, T_QUAKE1))

    # -------------------------------------------------------------------------------------------- sky
    def beams_layer(self, t, A, B, w, Rp, cx, cy, col_u):
        dx = self.hx - cx; dy = self.hy - cy; d = np.sqrt(dx * dx + dy * dy) + 1e-3; phi0 = np.arctan2(dy, dx)
        twist = 2.4 * ease(col_u) ** 1.3; spin = 0.06 * t + 1.4 * col_u ** 2
        phi = phi0 + twist * np.log(d / 30.0)
        reach = (900 + 1.0 * Rp) * (1 - 0.7 * ease(col_u))
        dd = np.maximum(d - Rp, 0)
        rad = (1 - np.exp(-(dd + 6) / 35)) * (np.exp(-dd / reach) * 0.9 + 0.12 * np.exp(-dd / (reach * 2.2)))
        acc = np.zeros(d.shape + (3,), f32)
        for b in self.beams:
            a = b["a"] + spin * b["sp"]
            dp = (phi - a + np.pi) % (2 * np.pi) - np.pi
            wd = b["w"] * (1 + 0.25 * math.sin(t * 0.9 * b["sp"] + b["ph"])) * (1 + 0.5 * min(Rp, 300) / 300)
            g = np.exp(-(dp / wd) ** 2 * 1.6)
            I = b["I"] * (0.72 + 0.28 * math.sin(t * 1.3 * b["sp"] + b["ph"] * 2))
            x = (b["hue"] + dp / wd * 0.25) % 1.0
            c = pal_list(A["beams"], x) * (1 - w) + pal_list(B["beams"], x) * w if w < 1 else pal_list(B["beams"], x)
            acc += c * (g * I)[..., None]
        return acc * rad[..., None] * 0.30 * lerp(A["bI"], B["bI"], w), d

    # -------------------------------------------------------------------------------------------- the planet
    def planet(self, img, st, t, cx, cy, R, kind, I, red, lit):
        """kind 'disc': the dark giant with crescent, thermal glow, lightning, aurora, refraction ring"""
        if kind == "dot":
            return
        if kind == "speck":                                                     # ~3 px: a dark dot with a dim red rim
            x0, y0 = int(cx - 6), int(cy - 6)
            yy, xx = np.mgrid[y0:y0 + 13, x0:x0 + 13].astype(f32)
            dd = np.sqrt((xx + 0.5 - cx) ** 2 + (yy + 0.5 - cy) ** 2)
            cov = np.clip(R + 0.5 - dd, 0, 1)[..., None]
            rim = np.exp(-((dd - R - 0.6) / 0.7) ** 2)[..., None] * np.array([0.08, 0.015, 0.008], f32) * I
            img[y0:y0 + 13, x0:x0 + 13] = img[y0:y0 + 13, x0:x0 + 13] * (1 - 0.93 * cov) + cov * np.array([0.010, 0.002, 0.001], f32) + rim
            return
        bd = self.pl["moon"] if R < 300 else self.pl["close"]
        scale = R / bd.Rp
        # refraction ring: stars just behind the limb, squeezed along it (from the star layer before the disc covers it)
        self.refraction(img, st, cx, cy, R, t, I)
        # faint red thermal halo just outside the limb
        def halo(d, dx, dy):
            o = np.maximum(d - R, 0)
            return (np.exp(-o / (0.012 * R + 1.5)) * 0.10 + np.exp(-o / (0.08 * R)) * 0.025)[..., None] * np.array([1.0, 0.18, 0.06], f32) * red * I
        splat(img, cx, cy, R * 1.35, halo)
        box = bd.render(img, cx, cy, t, I=I * lit, scale=scale)
        if box is None: return
        x0, x1, y0, y1, cov = box
        # night-side emission: thermal glow (deep red, ~800 K) + lightning, mapped on the sphere
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(f32)
        u = (xx + 0.5 - cx) / R; v = (yy + 0.5 - cy) / R
        r2 = u * u + v * v; inside = r2 < 1
        z = -np.sqrt(np.clip(1 - r2, 0, 1)); mu = -z
        M = bd.M.astype(f32)
        p = np.stack([u, v, z], -1) @ M.T
        lat = np.arcsin(np.clip(p[..., 1], -1, 1)); lon = np.arctan2(p[..., 0], p[..., 2]) - bd.spin * t + bd.lon0
        gm = cv2.remap(self.glow_map, ((lon / (2 * np.pi) + 0.5) % 1.0 * 1024).astype(f32),
                       np.clip((0.5 - lat / np.pi) * 512, 0, 511).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        s = MO.SUN.astype(f32); n = np.stack([u, v, z], -1)
        night = smooth(0.05, -0.25, n @ s)
        mx_ = ((lon / (2 * np.pi) + 0.5) % 1.0 * 1024).astype(f32); my_ = np.clip((0.5 - lat / np.pi) * 512, 0, 511).astype(f32)
        cm = cv2.remap(self.cloud_map, mx_, my_, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        # matte banded clouds, faintly visible by city skyglow / twilight: dark maroon belts, charcoal zones (no specular)
        zone = np.clip((cm - 0.75) / 0.55, 0, 1)[..., None]
        bands = (np.array([0.030, 0.0075, 0.006], f32) * (1 - zone) + np.array([0.014, 0.013, 0.016], f32) * zone) * cm[..., None]
        amb = bands * (0.55 + 0.45 * mu ** 0.6)[..., None] * inside[..., None] * (0.35 + 0.65 * min(red, 1.0))
        # deep-red thermal glow, strongest in the belts (deeper, hotter layers), mild limb darkening
        th = (mu ** 0.25 * gm ** 1.5 * night * inside)[..., None] * np.array([1.0, 0.11, 0.03], f32) * 0.020 * red + amb
        # lightning
        lt = np.zeros(u.shape, f32)
        for e in self.lightning:
            dt_ = t - e["t"]
            if dt_ < -0.01 or dt_ > e["dur"] + 0.25: continue
            fl = 0.0
            for k in range(e["n"]):
                tk = dt_ - k * 0.06
                if tk >= 0: fl += math.exp(-tk / 0.035) * (1 if k == 0 else 0.7)
            fl += 0.25 * math.exp(-max(dt_, 0) / 0.18)
            ex, ey = e["u"], e["v"]
            dd = np.sqrt(((u - ex) / 1.9) ** 2 + (v - ey) ** 2)
            lt += (np.exp(-dd / 0.025) * 1.4 + np.exp(-dd / 0.06) * 0.7) * fl * e["I"]
        lt *= inside * (0.4 + 0.6 * mu) * (0.25 + 0.9 * cm ** 1.5)          # cloud patches lit from within
        add = th + lt[..., None] * np.array([0.72, 0.84, 1.0], f32) * 1.6
        img[y0:y1, x0:x1] += add * cov[..., None] * I
        self.aurora(img, cx, cy, R, t, red * 0.8 * I)
        self._lt = float(lt.sum()) / max(R * R, 1.0)
        return float(lt.max()) if lt.size else 0.0

    def refraction(self, img, st, cx, cy, R, t, I):
        """atmospheric refraction at the limb (as in stellar occultations by Jupiter): the stars hidden in a thin annulus
        behind the limb reappear squeezed into a thin arc hugging it, flickering with the atmosphere's turbulence"""
        H, W = img.shape[:2]
        pad = int(R * 0.08) + 6
        x0, x1 = max(0, int(cx - R - pad)), min(W, int(cx + R + pad)); y0, y1 = max(0, int(cy - R - pad)), min(H, int(cy + R + pad))
        if x1 <= x0 or y1 <= y0: return
        sub = np.ascontiguousarray(st[y0:y1, x0:x1])
        na, nb = 2048, 24
        ang = np.linspace(0, 2 * np.pi, na, endpoint=False).astype(f32)
        rr = np.linspace(R * 0.86, R, nb).astype(f32)
        mx = (cx - x0 + rr[None, :] * np.cos(ang)[:, None]).astype(f32); my = (cy - y0 + rr[None, :] * np.sin(ang)[:, None]).astype(f32)
        pol = cv2.remap(sub, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        band = pol.sum(1) * (R * 0.14 / nb) * (2 * np.pi * R / na) * 2.5                         # stars behind the limb, per angle bin
        band = cv2.GaussianBlur(band[:, None, :], (0, 0), sigmaX=0.1, sigmaY=4).reshape(na, 3)
        flick = (0.65 + 0.35 * np.sin(ang * 37 + t * 5.0) * np.sin(ang * 13 - t * 3.1)).astype(f32)
        val = (band * flick[:, None]).astype(f32)
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(f32)
        dx_, dy_ = xx + 0.5 - cx, yy + 0.5 - cy
        d = np.sqrt(dx_ * dx_ + dy_ * dy_)
        ai = ((np.arctan2(dy_, dx_) % (2 * np.pi)) / (2 * np.pi) * na).astype(f32)
        v = cv2.remap(val[:, None, :].repeat(2, 1), np.zeros_like(ai), ai, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        prof = np.exp(-((d - R - 1.2) / 1.1) ** 2) * (d > R - 1)
        img[y0:y1, x0:x1] += v * (prof * 0.9 + np.exp(-np.maximum(d - R, 0) / 6.0) * 0.08 * (d > R - 1))[..., None] * I

    def aurora(self, img, cx, cy, R, t, amt):
        """auroral ovals round both magnetic poles (green O / red H-alpha tints), seen near the limb"""
        if amt <= 0.01: return
        P = self.pole
        for sgn in (1, -1):
            px, py = cx + sgn * P[0] * R * 0.80, cy + sgn * P[1] * R * 0.80
            ang = math.atan2(P[1], P[0])
            ca, sa = math.cos(ang), math.sin(ang)
            def fn(d, dx, dy, sgn=sgn):
                a_ = dx * ca + dy * sa; b_ = -dx * sa + dy * ca                     # a_: along the pole axis
                rr = np.sqrt((a_ / (0.14 * R)) ** 2 + (b_ / (0.42 * R)) ** 2)
                ring = np.exp(-((rr - 1) / 0.18) ** 2) * (0.8 + 0.2 * np.sin(np.arctan2(a_, b_) * 6 - t * 3 * sgn))
                curtain = np.exp(-((rr - 1.05) / 0.35) ** 2) * 0.25
                g = (ring + curtain)
                col = np.array([0.30, 1.0, 0.55], f32) * 0.7 + np.array([1.0, 0.25, 0.55], f32) * 0.3
                return g[..., None] * col * amt * 0.20
            splat(img, px, py, R * 0.6, fn)

    def shock(self, img, cx, cy, u, col, size=1.0, decay=0.55):
        R = 2400 * size * (max(u, 0) / 1.4) ** 0.6; wdt = (18 + 60 * u) * size
        dd = np.sqrt((self.xx - cx) ** 2 + (self.yy - cy) ** 2)
        for ch, off in ((0, 10), (1, 0), (2, -10)):
            img[..., ch] += np.exp(-((dd - R - off * size) / wdt) ** 2) * 2.0 * math.exp(-max(u, 0) / decay) * (0.6 + 0.4 * col[ch])

    def pointer(self, img, x, y, t, amt, col=(0.35, 1.0, 0.85), r0=30):
        if amt <= 0: return
        col = np.array(col, f32); r0 = r0 + 3 * math.sin(t * 5); ping = (t * 1.3) % 1.0
        def fn(d, dx, dy):
            ring = np.exp(-((d - r0) / 2.0) ** 2) * 1.8
            ang = np.arctan2(dy, dx) - t * 1.6
            br = np.exp(-((d - r0 - 14) / 2.4) ** 2) * (np.cos(ang * 4) > 0.55) * 2.0
            pg = np.exp(-((d - (r0 + 8 + 90 * ping)) / 3.0) ** 2) * (1 - ping) ** 1.5 * 1.4
            return (ring + br + pg)[..., None] * col * amt
        splat(img, x, y, r0 + 110, fn)

    def star(self, img, x, y, I, col=(1.0, 0.95, 0.85)):
        splat(img, x, y, 24, lambda d, dx, dy: ((np.exp(-d / 0.8) * 3 + np.exp(-d / 3) * 0.25
                                                 + (np.exp(-np.abs(dx) / 0.8) * np.exp(-np.abs(dy) / 9) + np.exp(-np.abs(dy) / 0.8) * np.exp(-np.abs(dx) / 9)) * 0.5)
                                                * I)[..., None] * np.array(col, f32))

    # -------------------------------------------------------------------------------------------- city
    def city(self, t, A, B, w, light_flash, red, q):
        fg = self.fg
        base = fg.rgb * 1.05
        # flicker: during the quakes, blocks of lights stutter and some die for a moment; a global brown-out dip
        if q > 0.01:
            g = 1 - q * (0.30 * (0.5 + 0.5 * math.sin(t * 23)) * (noise1(t, 5, 3.0) > 0.2) + 0.15)
            ph = self.cell
            ci = ((self.xx // 34).astype(np.int32) % 64); cj = ((self.yy // 34).astype(np.int32) % 64)
            cj = np.where(self.yy > YH + 40, 7, cj)                           # the street's reflections follow their column
            phase = ph[cj, ci]
            fl = 0.5 + 0.5 * np.sin(t * (9 + 6 * phase) + phase * 7)
            out_ = (fl < 0.22 + 0.25 * q) * q
            f = np.clip(g * (1 - out_ * 0.95), 0, 1)
            base = base - self.em * (1 - f)[..., None]
        # relight: the planet's red glow on the upper facades and skyline edges, lightning washes, skyglow
        rc = np.array(lerp(A["tint"], B["tint"], w), f32)
        base = base + (fg.flat * self.up_w[..., None] * 0.10 + self.rim[..., None] * 0.25) * rc * red
        if light_flash > 0:
            base = base + (fg.flat * (0.35 + 0.65 * self.up_w)[..., None] * 0.45 + self.rim[..., None] * 1.0) * \
                np.array([0.70, 0.80, 1.0], f32) * light_flash
        return base

    def street(self, img, skyimg, t, q):
        """wet asphalt: a rough mirror of the sky about eye level (stretched / blurred vertically, rippled when the ground
        shakes), weighted by the plate's glossiness"""
        H, W = self.L.H, self.L.W
        y0 = int(YH)
        ys = self.yy[y0:]; xs = self.xx[y0:]
        sy = np.clip(YH - (ys - YH) * 1.6 + q * 6 * np.sin(ys * 0.21 + t * 40), 0, YH - 1).astype(f32)   # rough, stretched lobe
        sm = cv2.resize(skyimg, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
        sm = cv2.GaussianBlur(sm, (0, 0), sigmaX=2, sigmaY=12)
        refl = cv2.remap(sm, (xs / 2).astype(f32), (sy / 2).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        R = 0.32 * self.wet[y0:]
        img[y0:] += refl * R[..., None]
        pl = getattr(self, "_pl", None)
        if pl is not None:                                                      # the dark disc dims the reflections under it
            cx, cy, Rp = pl
            dm = np.clip((Rp - np.sqrt((xs - cx) ** 2 + (sy - cy) ** 2)) / 25.0, 0, 1)
            dm = cv2.GaussianBlur(dm, (0, 0), sigmaX=10, sigmaY=30)
            img[y0:] *= (1 - 0.45 * self.wet[y0:] * dm)[..., None]
        fl = getattr(self, "_flash", 0.0)
        if fl > 0: img[y0:] += (self.wet[y0:] * fl * 1.6)[..., None] * np.array([0.65, 0.78, 1.0], f32)

    # -------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        fg = self.fg
        A, B, w, cur, t0, t1 = self.mix_params(t)
        S = SET[cur]
        pulse = 1 + 0.06 * math.sin(2 * math.pi * t / 1.6) + sum(0.40 * math.exp(-((t - tp) / 0.20) ** 2) for tp in PULSES)
        col_u = 0.0 if (t1 > 1e8 or cur == "close") else max(0.0, 1 - (t1 - t) / COLLAPSE)
        ps = planet_state(t, cur, t0)
        cx, cy = (ps[0], ps[1]) if ps else (600.0, 600.0)
        Rp = ps[2] if ps else 0.0
        g_in = back_out((t - t0) / BLOOM) if t0 > 0 else 1.0
        red = lerp(A["red"], B["red"], w)
        q = self.quake(t)
        bright = 1 + 0.5 * (pulse - 1)
        # sky
        sky = self.base_sky * (1 + 0.15 * (pulse - 1))
        gcol = np.array(lerp(A["glow"], B["glow"], w), f32)
        if Rp > 2:
            dd = np.maximum(np.sqrt((self.hx - cx) ** 2 + (self.hy - cy) ** 2) - Rp * g_in, 0)
            aure = (np.exp(-dd / (40 + 0.3 * Rp)) * 0.10 + np.exp(-dd / (250 + 0.8 * Rp)) * 0.035) * lerp(A["gl"], B["gl"], w) * bright
            sky = sky + aure[..., None] * gcol
        bm, _ = self.beams_layer(t, A, B, w, max(Rp, 4.0) * g_in, cx, cy, col_u)
        img = self.up(sky * (1 - 0.3 * col_u) + bm * (1 + 0.6 * col_u))
        sg = lerp(A["stars"], B["stars"], w)
        st = self.stars.render(self.cam, t, gain=1.0, twinkle=1.4, plate_gain=0.10, star_gain=1.0, cx=1500, cy=700, rot=-8.0) * sg * 0.9
        # the target star of the Neptune beat (and the end): blinks out as the dark planet covers it
        st_t = (640.0, 560.0 + 6 * (T_BLINK + 0.08 - T_SW["nep"]))
        st_I = 1.0
        if cur == "nep": st_I = 1 - ramp(t, T_BLINK + 0.02, T_BLINK + 0.12) * (1 - ramp(t, T_BLINK + 1.0, T_BLINK + 1.1))
        if cur == "odds" and t > T_END_BLINK - 0.3: st_I = 1 - ramp(t, T_END_BLINK + 0.05, T_END_BLINK + 0.15) * (1 - ramp(t, T_END_BLINK + 0.9, T_END_BLINK + 1.0))
        self.star(st, st_t[0], st_t[1], 1.4 * st_I, (0.85, 0.92, 1.0))
        if cur == "mars": self.star(st, 494.0, 552.0, 0.8, (1.0, 0.9, 0.8))     # a star the speck passes over
        img += st
        # the planet (and its light)
        flash = 0.0; self._pl = None
        if ps and ps[3] == "disc":
            I = pulse * (0.5 + 0.5 * min(max((t - t0) / BLOOM * 3, 0), 1) if cur != "close" or t < T_PASS0 else 1.0)
            R = ps[2] * (g_in if t - t0 < BLOOM else 1.0)
            if col_u > 0:
                R *= (1 + 0.25 * ease(col_u / 0.45)) if col_u < 0.45 else 1.25 * (1 - ease((col_u - 0.45) / 0.55) ** 0.7) + 0.02
            self._lt = 0.0
            fl = self.planet(img, st, t, cx, cy, R, "disc", I, red, 1.0)
            flash = min(self._lt * 6.0, 1.2) * 0.25
            self._pl = (cx, cy, R)
        elif ps and ps[3] == "speck":
            self.planet(img, st, t, cx, cy, ps[2], "speck", 1.0, 1.0, 1.0)
        if cur in ("nep", "mars"):
            pa = ramp(t, t0 + 0.3, t0 + 0.7) * (1 - col_u)
            px, py = (st_t if cur == "nep" else (cx, cy))
            self.pointer(img, px, py, t, pa * 0.8, col=(0.45, 0.85, 1.0) if cur == "nep" else (1.0, 0.55, 0.40), r0=26)
        if cur == "odds" and t > T_END_BLINK - 0.6:
            self.pointer(img, st_t[0], st_t[1], t, ramp(t, T_END_BLINK - 0.6, T_END_BLINK - 0.2) * (1 - ramp(t, DUR - 0.9, DUR - 0.4)) * 0.8,
                         col=(0.45, 0.85, 1.0), r0=26)
        skyimg = img.copy()
        # city + wet street
        light = 1.0 + 0.06 * (pulse - 1)
        city = self.city(t, A, B, w, flash, red, q) * light
        city = city + self.up(bm) * 0.04 * fg.a[..., None]
        a = fg.a[..., None]
        img = img * (1 - a) + city * a
        self._flash = flash
        self.street(img, skyimg, t, q)
        # swap flashes + chromatic shockwaves
        for ts, k in SWAPS:
            u = t - ts
            if -0.05 < u < 1.4 and k != "odds":
                NS = SET[k]
                fc = 0.4 + 0.6 * np.array(NS["glow"], f32) / max(max(NS["glow"]), 1e-3)
                img += (2.6 * math.exp(-max(u, 0) / 0.08) * ease((u + 0.05) / 0.05)) * fc
                p_ = planet_state(ts + 0.01, k, ts)
                sx, sy = (p_[0], p_[1]) if p_ else (600.0, 560.0)
                self.shock(img, sx, sy, u, fc)
        # white-out -> the normal city night
        if T_WO0 < t < T_BACK:
            v = ease((t - T_WO0) / (T_BACK - T_WO0)); img = img + (30 * v ** 2.5) * np.array([1.0, 0.92, 0.92], f32)
        if T_BACK <= t < T_BACK + 0.6:
            img = img + 30 * math.exp(-(t - T_BACK) / 0.10) * np.array([1.0, 0.92, 0.92], f32)
            self.shock(img, 560, 560, t - T_BACK, np.array([1.0, 0.6, 0.6], f32))
        img = self.chroma_bloom(img, 1.0)
        out = tonemap(img, 1.0)
        out = self.chroma(out, 1.0 + 3 * q)
        if q > 0.01:                                                            # the ground shakes (tripod and all)
            sx_ = q * 7 * noise1(t, 31, 9.0); sy_ = q * 5 * noise1(t, 37, 11.0)
            M_ = np.float32([[1.012, 0, -540 * 0.012 + sx_], [0, 1.012, -960 * 0.012 + sy_]])
            out = cv2.warpAffine(out, M_, (self.L.W, self.L.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        out = finish(out, t, grain=0.008, vignette=0.12)
        self.overlay(out, t, cur, t0)
        return out

    def chroma_bloom(self, img, amt):
        img = bloom(img, 0.85 * amt)
        H, W = img.shape[:2]
        sm = cv2.resize(img, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
        sm = np.maximum(sm - 1.0, 0); acc = np.empty_like(sm)
        for c, s in ((0, 26), (1, 20), (2, 15)): acc[..., c] = cv2.GaussianBlur(sm[..., c], (0, 0), s)
        return img + cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR) * 0.35 * amt

    def chroma(self, out, k_=1.0):
        W, H = self.L.W, self.L.H; o = out.copy()
        for ch, k in ((0, 1 + 0.0018 * k_), (2, 1 - 0.0018 * k_)):
            M = np.float32([[k, 0, (1 - k) * W / 2], [0, k, (1 - k) * H / 2]])
            o[..., ch] = cv2.warpAffine(out[..., ch], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return o

    def overlay(self, out, t, cur, t0):
        L = self.L; W = L.W
        S = SET[cur] if not (cur == "close" and t >= T_PASS0 - 0.1) else FLYBY
        start = LN["hook_b"]["start"] if cur == "hook" else (T_PASS0 if S is FLYBY else t0)
        a = ramp(t, start + 0.15, start + 0.45)
        nxt = [ts for ts, k in SWAPS if ts > t] + ([T_PASS0 - 0.1] if cur == "close" and t < T_PASS0 - 0.1 else [])
        if nxt: a *= 1 - ramp(t, min(nxt) - 0.35, min(nxt) - 0.15)
        if T_WO0 < t < T_BACK: a = 0.0
        if cur == "odds": a *= 1 - ramp(t, LN["end"]["start"] - 0.2, LN["end"]["start"] + 0.2)
        if a > 0.01 and S["name"]:
            dy = (1 - a) * 18
            big = int(L.hud_size * (1.35 if len(S["name"]) < 12 else 1.10))
            rgba, _ = word_layer(S["name"], big, W * 0.9, fill=S["tc"])
            composite(out, rgba, W / 2, RO_Y[0] + dy, a)
            hud_text(out, S["l2"], W / 2, RO_Y[1] + dy, int(L.hud_size * 0.58), "Black", (255, 255, 255), a, 0.08, display=True)
            hud_text(out, S["l3"], W / 2, RO_Y[2] + dy, int(L.hud_size * 0.46), "Bold", (240, 236, 236), a, 0.10, display=True)
        self.caps.draw(out, t)


def run_stills(ts):
    sc = Scene(); os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
    for t in ts:
        t0 = time.time(); im = sc.frame(t)
        Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(SCR, "stills", f"{t:05.2f}.png"))
        print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "info":
        print("DUR", DUR, "R moon/close/mars px", round(R_MOON_PX, 1), round(R_CLOSE_PX, 1), round(R_MARS_PX, 2))
        print({k: round(v, 2) for k, v in T_SW.items()}, "blink", round(T_BLINK, 2), "pass", round(T_PASS0, 2), round(T_PASS1, 2),
              "back", round(T_BACK, 2), "quake", round(T_QUAKE0, 2), round(T_QUAKE1, 2)); sys.exit()
    if sys.argv[1] == "segs":
        from lib.v3_redo_q5 import render_segments
        render_segments(sys.modules[__name__]); sys.exit()
    if sys.argv[1] == "stills":
        run_stills([float(x) for x in sys.argv[2].split(",")])
