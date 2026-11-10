"""THE DINOSAUR-KILLER ASTEROID, SEEN FROM THE GROUND -- one LOCKED tripod shot of the park (A_park), VFX spectacle style.
The park stands in for "if you were standing ~1,000 km from Chicxulub". Time is compressed; a T+ counter says how much.
  hook    bright day park, rainbow sun beams; a new bright star appears high on the right
  appr    the star brightens and grows, then ignites into a blazing plasma fireball with a long ionised trail
  hit     it disappears behind the horizon: white flash, chromatic shockwave ring, a fireball dome and a mushroom plume
          with rim light climb above the skyline; heat distortion; the park is relit orange-white
  quake   (T+ minutes) a ground jolt (a few frames of shake: the ground itself moves), dust kicked up, rumble
  ejecta  (T+ 15-45 min) hundreds of glowing meteor streaks fill a red-hot sky; the park is lit infernal orange,
          the trees and grass smoke, embers rise
  blast   (T+ ~1 h) a dust wall rolls in from the horizon, shock ring, wind; then impact winter: a brown-grey sky with a
          dim red sun and falling ash (dim but readable)
  end     golden white-out -> the sunny green park again ("66 million years later") -- loops to the first frame
Built on docs-series/shorts/lib (read-only). Style copied from ../other-suns/short.py (beams, flash, chromatic rings,
readouts, relighting, chroma bloom).
Usage (one heavy process at a time, under nice):
  /home/user/ttsenv/bin/python short.py info
  /home/user/ttsenv/bin/python short.py vert|wide              full render -> SCR/video_<tag>.mp4
  /home/user/ttsenv/bin/python short.py vert|wide 1.0,9.5      stills -> SCR/stills/<tag>_<t>.png
  /home/user/ttsenv/bin/python short.py patch vert 3.9:5.2     re-render only those time ranges
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (sets up pylib path)
import numpy as np, cv2
from PIL import Image
from lib.core import f32, Layout, ramp, smooth, ease, noise1, splat, lum, fbm2, bbcolor, kf
from lib.foreground import Foreground
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish, Encoder
from lib.audio import place

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S13-asteroid"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/A_park.png"
FPS = 30
LEAD, TAIL = 0.25, 1.05
IMP_SRC_X = 665.0                                     # impact azimuth (behind the white building), SOURCE px

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]


# ------------------------------------------------------------------------------------------------ timeline
T_STAR = 0.85                                         # the new star appears
T_IMP = wt("hit", "BEYOND") - 0.12                    # bolide drops behind the horizon -> flash
T_ENTRY = T_IMP - 4.6                                 # atmospheric entry: plasma ignites
T_FLASHW = wt("hit", "FLASH")
T_Q0 = LN["quake"]["start"]
T_JOLT = wt("quake", "HEAVES") - 0.05                 # seismic waves arrive
T_JOLT2 = wt("quake", "TEN") - 0.05
T_EJ0 = wt("ejecta", "MOLTEN") - 0.25                 # ejecta re-entry begins
T_RED = wt("ejecta", "SKY")
T_FIRE = wt("ejecta", "IGNITE") - 0.4
T_BL0 = LN["blast"]["start"]                          # dust wall appears on the horizon
T_HITS = wt("blast", "HITS") - 0.05                   # the air blast reaches us
T_SOOT = wt("blast", "SOOT") - 0.2                    # impact winter
T_75 = wt("blast", "THREE") - 0.1
T_WO0 = LN["end"]["start"] - 0.65                     # golden white-out
T_BACK = LN["end"]["start"] - 0.05                    # sunny park again
PULSES = [wt("appr", "APPEARS"), wt("appr", "10 KM"), wt("appr", "20 KM/S"), T_FLASHW, wt("hit", "FIREBALL"), T_JOLT2,
          wt("ejecta", "RED-HOT"), wt("blast", "VANISH"), wt("end", "HERE")]


def lerp(a, b, w): return tuple(x + (y - x) * w for x, y in zip(a, b)) if isinstance(a, tuple) else a + (b - a) * w


# ------------------------------------------------------------------------------------------------ looks per phase
DAY = dict(zen=(0.012, 0.075, 0.42), hor=(0.30, 0.50, 0.85), gain=1.0, tint=(1.0, 0.98, 0.95), flat=0.0, amb=0.10, sat=1.0,
           sunI=1.0, beams=1.0, expo=1.0)
APPR = dict(zen=(0.010, 0.060, 0.36), hor=(0.32, 0.46, 0.78), gain=1.05, tint=(1.0, 0.97, 0.95), flat=0.05, amb=0.10, sat=1.05,
            sunI=0.9, beams=0.6, expo=1.0)
FIRE = dict(zen=(0.08, 0.05, 0.11), hor=(0.80, 0.38, 0.15), gain=1.25, tint=(1.0, 0.62, 0.32), flat=0.25, amb=0.25, sat=1.25,
            sunI=0.5, beams=0.0, expo=0.95)
QUAKE = dict(zen=(0.09, 0.04, 0.07), hor=(0.70, 0.28, 0.10), gain=1.05, tint=(1.0, 0.55, 0.26), flat=0.30, amb=0.25, sat=1.25,
             sunI=0.4, beams=0.0, expo=1.0)
RED = dict(zen=(0.15, 0.018, 0.014), hor=(0.75, 0.13, 0.03), gain=0.95, tint=(1.0, 0.36, 0.11), flat=0.50, amb=0.45, sat=1.55,
           sunI=0.15, beams=0.0, expo=1.0)
DUST = dict(zen=(0.11, 0.065, 0.040), hor=(0.36, 0.20, 0.10), gain=0.45, tint=(1.0, 0.62, 0.38), flat=0.6, amb=0.4, sat=0.55,
            sunI=0.10, beams=0.0, expo=1.25)
WINTER = dict(zen=(0.050, 0.044, 0.042), hor=(0.150, 0.105, 0.075), gain=0.26, tint=(0.95, 0.80, 0.68), flat=0.65, amb=0.45, sat=0.30,
              sunI=0.12, beams=0.0, expo=1.55)
KEYS = [(0.0, DAY), (T_ENTRY - 1.0, DAY), (T_IMP - 0.4, APPR), (T_IMP + 0.3, FIRE), (T_Q0, FIRE), (T_JOLT, QUAKE), (T_EJ0, QUAKE),
        (T_RED, RED), (T_BL0 + 0.6, RED), (T_HITS, DUST), (T_SOOT + 1.0, WINTER), (T_WO0, WINTER), (T_BACK, DAY), (999, DAY)]


def look(t):
    for (t0, A), (t1, B) in zip(KEYS, KEYS[1:]):
        if t0 <= t < t1:
            w = ease((t - t0) / (t1 - t0)) if t1 > t0 else 1.0
            if A is B or w <= 0: return A
            if t >= T_WO0 and t < T_BACK: w = float(t >= T_BACK - 0.12)      # hard swap hidden by the white-out
            return {k: lerp(A[k], B[k], w) for k in A}
    return DAY


# ------------------------------------------------------------------------------------------------ colour helpers
def palette(x):
    x = x[..., None] if np.ndim(x) else x
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (x - np.array([0.0, 0.33, 0.67], f32)))
    return (c ** 2.2).astype(f32)


def pal_list(cols, x):
    C = np.array(cols + [cols[0]], f32); n = len(cols)
    p = (x % 1.0) * n; i = np.floor(p).astype(np.int32); fr = (p - i)[..., None]
    return C[i] * (1 - fr) + C[i + 1] * fr


FIRE_RAMP = [(0.00, (0.10, 0.012, 0.006)), (0.25, (0.55, 0.06, 0.012)), (0.50, (1.40, 0.26, 0.04)), (0.75, (2.6, 0.85, 0.14)),
             (1.00, (4.0, 2.0, 0.55)), (1.30, (6.0, 4.6, 2.6)), (1.7, (9.0, 8.5, 7.5))]
_FX = np.array([p[0] for p in FIRE_RAMP], f32); _FC = np.array([p[1] for p in FIRE_RAMP], f32)
def fire_col(v):
    v = np.clip(v, 0, 1.7)
    return np.stack([np.interp(v, _FX, _FC[:, c]) for c in range(3)], -1).astype(f32)


def sample(tex, u, v):
    """wrap-sample a 2-D tile at float coords"""
    return cv2.remap(tex, (u % tex.shape[1]).astype(f32), (v % tex.shape[0]).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


# ------------------------------------------------------------------------------------------------ scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(vertical); W, H = L.W, L.H; self.vertical = vertical
        self.fg = fg = Foreground(FG_PATH, L, lamps=[], hz_frac=0.68)
        self.hz = hz = float(fg.horizon)
        self.k = 1.0 if vertical else 0.62                                   # effect scale
        self.IMP = (IMP_SRC_X * fg.s, hz + 6)
        if vertical:
            self.SUN = (255.0, 330.0); self.A0 = (985.0, 250.0)
        else:
            self.SUN = (1010.0, 150.0); self.A0 = (1830.0, 70.0)
        # half-res grid
        hw, hh = W // 2, H // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.hx, self.hy = xx, yy
        el = np.clip((hz - yy) / hz, 0, 1)
        self.k_hor = np.exp(-el / 0.33)[..., None].astype(f32)
        self.el = el
        yyf, xxf = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xxf, yyf
        r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 7 + r.uniform(-0.25, 0.25), w=r.uniform(0.16, 0.28), I=r.uniform(0.8, 1.2), hue=r.uniform(0, 1),
                           rainbow=bool(i % 3 != 2), ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(7)]
        self.N1 = fbm2((256, 256), 31, 2.3); self.N2 = fbm2((256, 256), 32, 1.7); self.N3 = fbm2((256, 256), 33, 2.8)
        self.mist = np.clip(fbm2((512, 512), 41, 2.6) * 0.5 + 0.45, 0, 1).astype(f32)
        self.shim = fbm2((256, 256), 81, 2.0)
        # foreground prep
        a = fg.a
        sh = np.zeros_like(a); sh[10:] = a[:-10]
        self.rim = cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 3.0) * a                  # top edges (sky-lit)
        self.rim_soft = cv2.GaussianBlur(np.clip(a - np.roll(a, 40, 0), 0, 1), (0, 0), 14.0) * a
        self.tree = (a * (1 - fg.ground)).astype(f32)
        # smoke source zone: above the foliage / skyline, half-res
        th = cv2.resize(self.tree, (hw, hh), interpolation=cv2.INTER_AREA)
        zone = np.zeros_like(th)
        for kk in range(0, 360, 24): zone = np.maximum(zone, np.roll(th, -kk // 2, 0) * math.exp(-kk / 260))
        gnd = cv2.resize(fg.ground, (hw, hh), interpolation=cv2.INTER_AREA)
        self.smoke_zone = cv2.GaussianBlur(np.maximum(zone, gnd * 0.55), (0, 0), 14).astype(f32)
        # fire spots on foliage and grass
        rr = np.random.default_rng(12)
        idx = np.flatnonzero(((self.tree > 0.9) | ((fg.ground > 0.9) & (yyf < hz + 260))).ravel())
        pick = rr.choice(idx, 140, replace=False)
        self.fire_xy = np.stack([pick % W, pick // W], 1).astype(f32)
        self.fire_ph = rr.uniform(0, 6.28, 140); self.fire_fr = rr.uniform(3, 9, 140); self.fire_t = rr.uniform(0, 1.8, 140)
        # embers
        er = np.random.default_rng(9); n = 420
        self.emb = dict(x=er.uniform(0, W, n), y0=er.uniform(0, 1, n), sp=er.uniform(0.07, 0.22, n), ph=er.uniform(0, 6.28, n),
                        sz=er.uniform(0.3, 1.0, n) ** 2, wob=er.uniform(5, 30, n))
        # ash flakes (winter)
        ar = np.random.default_rng(10); n = 600
        self.ash = dict(x=ar.uniform(0, W, n), y0=ar.uniform(0, 1, n), sp=ar.uniform(0.04, 0.12, n), ph=ar.uniform(0, 6.28, n),
                        sz=ar.uniform(0.3, 1.0, n), wob=ar.uniform(8, 40, n))
        # ejecta meteors
        mr = np.random.default_rng(21); n = 1500
        u = mr.uniform(0, 1, n)
        ts = T_EJ0 + (T_HITS + 0.6 - T_EJ0) * u ** 0.85
        x0 = mr.uniform(-0.15, 1.15, n) * W; y0 = mr.uniform(-0.25, 0.42, n) * hz
        side = np.sign(x0 - self.IMP[0] + mr.uniform(-80, 80, n))
        ang = mr.uniform(0.25, 1.25, n)                                               # rad below horizontal
        spd = mr.uniform(700, 2100, n) * (0.8 + 0.2 * self.k)
        self.met = dict(ts=ts, life=mr.uniform(0.35, 1.1, n), x0=x0, y0=y0, vx=side * np.cos(ang) * spd, vy=np.sin(ang) * spd,
                        tl=mr.uniform(0.08, 0.22, n), I=mr.uniform(0.4, 1.0, n) ** 2 * 1.0, big=mr.uniform(0, 1, n) > 0.94,
                        hue=mr.uniform(0, 1, n))
        # dust motes (blast)
        dr = np.random.default_rng(14); n = 500
        self.mote = dict(x=dr.uniform(0, W, n), y=dr.uniform(0.0, 1.0, n) * H, sp=dr.uniform(500, 1600, n), sz=dr.uniform(0.3, 1, n))
        emph = {"DINOSAUR-KILLER", "1,000 KM", "10 KM", "20 KM/S", "FLASH", "SUN", "FIREBALL", "SPACE", "HEAVES", "TEN", "RED-HOT",
                "IGNITE", "BLAST", "YEARS", "VANISH", "HERE", "MOLTEN", "STAR"}
        self.caps = Captions(L, WORDS, emphasis=emph)
        L.cap_y = 1010 if vertical else 590

    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    # -------------------------------------------------------------------------------------------- sky pieces (half-res)
    def beams_layer(self, t, C, cols, reach=1500, spin0=0.0, wmul=1.0):
        dx = self.hx - C[0]; dy = self.hy - C[1]
        d = np.sqrt(dx * dx + dy * dy) + 1e-3; phi = np.arctan2(dy, dx)
        rad = (1 - np.exp(-(d + 6) / 35)) * (np.exp(-d / reach) * 0.9 + 0.12 * np.exp(-d / (reach * 2.2)))
        acc = np.zeros(dx.shape + (3,), f32); spin = 0.06 * t + spin0
        for b in self.beams:
            a = b["a"] + spin * b["sp"]
            dp = (phi - a + np.pi) % (2 * np.pi) - np.pi
            wd = b["w"] * wmul * (1 + 0.25 * math.sin(t * 0.9 * b["sp"] + b["ph"]))
            g = np.exp(-(dp / wd) ** 2 * 1.6)
            I = b["I"] * (0.72 + 0.28 * math.sin(t * 1.3 * b["sp"] + b["ph"] * 2))
            x = (b["hue"] + dp / wd * 0.32) % 1.0 if b["rainbow"] else np.full(dp.shape, b["hue"], f32)
            c = palette(x) if cols is None else pal_list(cols, x)
            acc += c * (g * I)[..., None]
        return acc * rad[..., None] * 0.38

    def asteroid(self, t):
        """new star -> plasma fireball with a long ionised trail (half-res additive layer) and its light level"""
        if t < T_STAR or t > T_IMP + 3.5: return None, 0.0
        A = np.array(self.A0, f32) / 2; B = np.array(self.IMP, f32) / 2 + np.array([0, 10], f32)
        D = B - A; Ln = float(np.hypot(*D)); dn = D / Ln
        P = 1.5; s_e = 0.12
        def s_of(tt):
            if tt < T_ENTRY: return s_e * ((tt - T_STAR) / (T_ENTRY - T_STAR)) ** 1.5
            return s_e + (1 - s_e) * min(1.0, (tt - T_ENTRY) / (T_IMP - T_ENTRY)) ** P
        sh = s_of(min(t, T_IMP)); head = A + D * sh
        lay = np.zeros(self.hx.shape + (3,), f32)
        ent = ramp(t, T_ENTRY - 0.3, T_ENTRY + 1.2)                         # plasma ignition
        # ---- ionised trail (age-based: hot core cools to orange, the train glows blue-violet and widens)
        if t > T_ENTRY:
            px = (self.hx * 0.5 - 0.5) - A[0]; py = (self.hy * 0.5 - 0.5) - A[1]
            px = (self.hx - 1) / 2 - A[0]; py = (self.hy - 1) / 2 - A[1]
            sp = (px * dn[0] + py * dn[1]) / Ln; pp = (-px * dn[1] + py * dn[0])
            u = np.clip((sp - s_e) / (1 - s_e), 0, 1) ** (1 / P)
            tp = T_ENTRY + u * (T_IMP - T_ENTRY); age = np.maximum(t - tp, 0)
            valid = (sp > s_e - 0.02) & (sp < sh) & (age > 0)
            w = (1.0 + 3.2 * age + 1.2 * ent) * self.k + 0.5
            n = sample(self.N1, sp * Ln * 0.35 - t * 6, pp * 0.6) * 0.5 + sample(self.N2, sp * Ln * 0.9, pp * 1.5 + t * 3) * 0.3
            tex = np.clip(1 + 0.55 * n, 0.2, 2.0)
            core = np.exp(-(pp / (w * 0.45)) ** 2) * np.exp(-age / 0.5) * 6.0
            glow = np.exp(-(pp / (w * 1.4)) ** 2) * (np.exp(-age / 1.0) * 2.6 + np.exp(-age / 3.5) * 0.6) * tex
            halo = np.exp(-np.abs(pp) / (w * 3.5)) * np.exp(-age / 1.8) * 0.25
            fade_in = np.clip((sp - s_e) * 25, 0, 1)
            m = (valid * fade_in * ent * (1 - ramp(t, T_IMP + 1.0, T_IMP + 3.4))).astype(f32)
            cool = np.clip(age / 1.2, 0, 1)[..., None]
            ccore = np.array([1.0, 0.95, 0.85], f32) * (1 - cool) + np.array([1.0, 0.55, 0.18], f32) * cool
            # chromatic train: red outer, blue-violet inner sheath
            ion = np.stack([np.exp(-(pp / (w * 1.25)) ** 2), np.exp(-(pp / (w * 0.9)) ** 2) * 0.55, np.exp(-(pp / (w * 0.75)) ** 2) * 1.15], -1)
            ion = np.stack([np.exp(-(pp / (w * 2.6)) ** 2), np.exp(-(pp / (w * 2.2)) ** 2) * 0.6, np.exp(-(pp / (w * 1.9)) ** 2) * 1.2], -1) - ion * 0.6
            ionc = np.maximum(ion, 0) * (np.exp(-age / 2.5) * 0.9 * tex)[..., None] * np.array([0.40, 0.45, 1.0], f32)
            lay += (core[..., None] * ccore + glow[..., None] * np.array([1.0, 0.45, 0.12], f32) + ionc + halo[..., None] * np.array([1.0, 0.5, 0.25], f32)) * m[..., None]
        # ---- head
        if t <= T_IMP + 0.02:
            hx, hy = float(head[0]), float(head[1])
            star = ramp(t, T_STAR, T_STAR + 0.5)
            grow = ramp(t, T_STAR, T_ENTRY)
            tw = 1 + 0.25 * math.sin(t * 23) * (1 - ent)
            rc = (1.0 + 1.0 * grow + 3.2 * ent) * self.k
            Ih = (6 + 24 * grow) * star * tw + 26 * ent
            pul = 1 + sum(0.8 * math.exp(-((t - tp) / 0.2) ** 2) for tp in PULSES[:3])
            Ih *= pul
            def fn(d, dx_, dy_):
                along = -(dx_ * dn[0] + dy_ * dn[1]); perp = np.abs(-dx_ * dn[1] + dy_ * dn[0])
                comet = np.exp(-perp / (rc * 0.9 + 1.5)) * np.exp(-np.maximum(along, 0) / (rc * 6 + 2)) * (along > -rc) * ent * 1.4
                bow = np.exp(-((d - rc * 1.4) / (rc * 0.5 + 0.8)) ** 2) * (along < 0) * ent * 0.8
                v = np.exp(-(d / rc) ** 2) * 1.0 + np.exp(-d / (rc * 2.5 + 2)) * 0.12 + np.exp(-d / (rc * 10 + 8)) * 0.010
                return (v * Ih)[..., None] * np.array([1.0, 0.92, 0.82], f32) + (comet * Ih * 0.12)[..., None] * np.array([1.0, 0.6, 0.25], f32) \
                    + (bow * Ih * 0.10)[..., None] * np.array([0.6, 0.7, 1.0], f32)
            splat(lay, hx, hy, min(420, rc * 60 + 40), fn)
            # 4-point twinkling spikes while it is still a star
            if ent < 1:
                for kk in range(4):
                    a = kk * math.pi / 2 + 0.4
                    def sp_fn(d, dx_, dy_, a=a):
                        al = dx_ * math.cos(a) + dy_ * math.sin(a); pp_ = np.abs(-dx_ * math.sin(a) + dy_ * math.cos(a))
                        return (np.exp(-pp_ / 0.7) * np.exp(-np.abs(al) / (18 + 30 * grow)) * Ih * 0.08 * (1 - ent))[..., None] * np.array([0.9, 0.95, 1.0], f32)
                    splat(lay, hx, hy, 160, sp_fn)
        light = (0.03 * ramp(t, T_STAR, T_ENTRY) + 0.7 * ent * ramp(t, T_ENTRY, T_IMP) ** 1.5) * (t <= T_IMP)
        return lay, light

    def plume(self, t, sky_amb, flash):
        """fireball dome + mushroom plume above the horizon (half-res): returns (bbox, rgb, alpha) or None"""
        tau = t - T_IMP
        if tau < 0: return None
        k = self.k
        bx, by = self.IMP[0] / 2, self.IMP[1] / 2
        Rd = k * 250 * (1 - math.exp(-tau / 0.7))
        t2 = max(tau - 0.5, 0)
        Hc = k * 390 * (1 - math.exp(-t2 / 3.0)) + k * 6 * t2
        Rc = k * (50 + 205 * (1 - math.exp(-t2 / 2.8)) + 3 * t2)
        ws = k * (30 + 60 * (1 - math.exp(-tau / 2.5)))
        span = max(Rd * 1.5, Rc * 1.4, ws * 3) + 60 * k
        x0, x1 = int(max(0, bx - span)), int(min(self.hx.shape[1], bx + span))
        y0, y1 = int(max(0, by - Hc - Rc * 0.8 - 70 * k)), int(min(self.hx.shape[0], by + 4))
        if x1 <= x0 or y1 <= y0: return None
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(f32)
        X = xx - bx; Y = by - yy
        ry = Rd * (0.95 - 0.55 * ramp(tau, 1.5, 9.0)) + 1; rx = Rd * (1.35 + 0.5 * ramp(tau, 1.5, 9.0)) + 1
        sd_d = (np.sqrt((X / rx) ** 2 + (Y / ry) ** 2) - 1) * ry
        wy = ws * (1 + 1.6 * np.exp(-np.maximum(Y, 0) / (0.18 * Hc + 8)))
        sd_s = np.maximum(np.maximum(np.abs(X) - wy, Y - Hc), -Y)
        rcy = Rc * 0.56
        sd_c = (np.sqrt((X / Rc) ** 2 + ((Y - Hc) / rcy) ** 2) - 1) * rcy
        # rolling torus lobes under the cap edge
        sd_t = np.sqrt((np.abs(X) - Rc * 0.78) ** 2 + ((Y - Hc + rcy * 0.35) * 1.3) ** 2) - Rc * 0.30
        sd = smin(sd_d, smin(sd_s, smin(sd_c, sd_t, 18 * k), 30 * k), 34 * k) if Hc > 4 else sd_d
        sz = max(Rc, Rd, 30.0)
        sc1 = sz / 2.2 + 6; sc2 = sz / 5 + 3
        n1 = sample(self.N1, X / sc1 * 9 + 0.3 * tau, (Y - 22 * tau * k) / sc1 * 9)
        n2 = sample(self.N2, X / sc2 * 9 - 2 * tau, (Y - 40 * tau * k) / sc2 * 9)
        n = 0.8 * n1 + 0.2 * n2
        disp = sd + (0.09 * sz + 5) * n
        edge = 3.0 + 0.012 * sz
        dens = smooth(edge, -edge, disp)
        inner = np.clip(-disp / (0.30 * sz + 8), 0, 1)
        heat = kf(tau, [(0, 1.75), (0.6, 1.5), (2.5, 1.12), (6, 0.88), (10, 0.66), (16, 0.42), (24, 0.22), (30, 0.12)])
        low = np.exp(-np.maximum(Y, 0) / (0.6 * Hc + 0.9 * Rd + 20))              # hotter near the ground / base
        capglow = np.exp(-((Y - Hc + rcy * 0.4) / (rcy * 0.8 + 4)) ** 2) * 0.35  # cap lit from beneath
        T = heat * (0.30 + 0.85 * inner) * (0.55 + 0.45 * low + capglow) * (0.80 + 0.20 * n)
        emis = fire_col(T)
        # rim light: outer shell lit by the sky / flash, strongest on the upper-left side (sun / sky)
        shell = dens * np.clip(1 - inner * 2.8, 0, 1)
        rimc = np.array(sky_amb, f32) * 2.0 + flash * np.array([1.0, 0.95, 0.85], f32) * 0.25 + np.array([1.0, 0.55, 0.22], f32) * heat * 0.9
        dirn = np.clip(0.6 - 0.4 * X / (sz + 1) + 0.3 * np.clip(Y / (Hc + Rd + 1), 0, 1), 0.2, 1.3)
        smoke = np.array([0.05, 0.035, 0.03], f32) * (np.array(sky_amb, f32) * 2 + 0.2)
        col = emis + smoke * (1 - 0.5 * inner)[..., None] + (shell * dirn)[..., None] * rimc
        alpha = (dens * (0.97 - 0.25 * ramp(tau, 18, 26))).astype(f32)
        return (x0, y0, x1, y1), col.astype(f32), alpha

    def meteors(self, t, amt):
        hw, hh = self.hx.shape[1], self.hx.shape[0]
        lay = np.zeros((hh, hw, 3), f32)
        m = self.met
        age = t - m["ts"]; sel = np.nonzero((age > 0) & (age < m["life"]))[0]
        for i in sel:
            a = age[i]; fr = a / m["life"][i]
            env = math.sin(math.pi * min(fr * 1.4, 1.0)) ** 0.6 * (1 - fr) ** 0.5
            hx = (m["x0"][i] + m["vx"][i] * a) / 2; hy = (m["y0"][i] + m["vy"][i] * a) / 2
            tl = min(m["tl"][i], a + 0.02)
            I = m["I"][i] * env * amt * (3.0 if m["big"][i] else 1.0)
            nseg = 5
            for s in range(nseg):
                u0, u1 = s / nseg, (s + 1) / nseg
                xa = hx - m["vx"][i] / 2 * tl * u0; ya = hy - m["vy"][i] / 2 * tl * u0
                xb = hx - m["vx"][i] / 2 * tl * u1; yb = hy - m["vy"][i] / 2 * tl * u1
                g = I * (1 - u0) ** 1.6
                c = (g * 1.0, g * (0.55 - 0.35 * u0), g * (0.20 - 0.15 * u0))
                cv2.line(lay, (int(xa * 4), int(ya * 4)), (int(xb * 4), int(yb * 4)), c, 2 if m["big"][i] else 1, cv2.LINE_8, 2)
            cv2.circle(lay, (int(hx * 4), int(hy * 4)), 4 * (2 if m["big"][i] else 1), (I * 6, I * 5, I * 3.5), -1, cv2.LINE_8, 2)
        if not len(sel): return lay
        return lay * 1.2 + cv2.GaussianBlur(lay, (0, 0), 2.0) * 3.0 + cv2.GaussianBlur(lay, (0, 0), 7.0) * 3.0

    # -------------------------------------------------------------------------------------------- foreground FX
    def relight(self, P, light, lightcol, rimI):
        fg = self.fg
        base = fg.rgb * (1 - P["flat"]) + fg.flat * P["flat"]
        y = lum(base)[..., None]; base = y + (base - y) * P["sat"]
        sky_amb = np.array(P["zen"], f32) * 0.5 + np.array(P["hor"], f32) * 0.5
        out = base * np.array(P["tint"], f32) * P["gain"] + fg.flat * sky_amb * P["amb"]
        out = out * light + fg.flat * np.array(lightcol, f32) * 0.0
        out += (self.rim * 0.9 + self.rim_soft * 0.3)[..., None] * np.array(lightcol, f32) * rimI
        return out

    def smoke(self, t, amt, col, glow):
        if amt <= 0: return None, None
        sx, sy = self.hx, self.hy
        n = sample(self.mist, sx * 0.40 + 6 * t + 30 * np.sin(sy / 210 + t * 0.6), sy * 0.45 + t * 70)
        n2 = sample(self.mist, sx * 0.9 - 9 * t, sy * 0.8 + t * 120)
        m = np.clip((n * 0.7 + n2 * 0.5) * 1.6 - 0.55, 0, 1) * self.smoke_zone * amt
        m = cv2.GaussianBlur(m, (0, 0), 2.5)
        hz2 = self.hz / 2
        under = np.exp(-np.clip(sy - hz2, -300, 300) ** 2 / 9000) * glow
        rgb = np.array(col, f32) + under[..., None] * np.array([1.2, 0.35, 0.06], f32)
        return self.up(m), self.up(rgb)

    def embers(self, t, amt, wind=0.0):
        W, H = self.L.W, self.L.H; e = self.emb
        y = H * (1.05 - ((e["y0"] + e["sp"] * t) % 1.0) * 1.1)
        x = (e["x"] + e["wob"] * np.sin(t * 1.3 + e["ph"]) + 40 * np.sin(y / 300 + e["ph"]) + wind * (t * 600 + e["ph"] * 300)) % W
        lay = np.zeros((H // 2, W // 2), f32)
        xi = np.clip((x / 2).astype(int), 0, W // 2 - 1); yi = np.clip((y / 2).astype(int), 0, H // 2 - 1)
        tw = 0.6 + 0.4 * np.sin(t * 7 + e["ph"] * 3)
        np.add.at(lay, (yi, xi), e["sz"] * tw * amt)
        lay = cv2.GaussianBlur(lay, (0, 0), 0.9) * 14 + cv2.GaussianBlur(lay, (0, 0), 4.0) * 7
        return self.up(lay)[..., None] * np.array([1.0, 0.45, 0.10], f32)

    def ash_layer(self, t, amt):
        W, H = self.L.W, self.L.H; e = self.ash
        y = H * (((e["y0"] + e["sp"] * t) % 1.0) * 1.1 - 0.05)
        x = (e["x"] + e["wob"] * np.sin(t * 0.9 + e["ph"]) + 25 * t) % W
        lay = np.zeros((H // 2, W // 2), f32)
        xi = np.clip((x / 2).astype(int), 0, W // 2 - 1); yi = np.clip((y / 2).astype(int), 0, H // 2 - 1)
        np.add.at(lay, (yi, xi), e["sz"] * amt)
        lay = cv2.GaussianBlur(lay, (0, 0), 1.0) * 1.2 + cv2.GaussianBlur(lay, (0, 0), 2.5) * 0.6
        return self.up(lay)

    def fire_spots(self, t, amt):
        if amt <= 0: return None
        W, H = self.L.W, self.L.H
        lay = np.zeros((H // 2, W // 2), f32)
        on = np.clip((t - T_FIRE - self.fire_t) / 0.6, 0, 1)
        fl = 0.55 + 0.45 * np.sin(t * self.fire_fr + self.fire_ph) * np.sin(t * self.fire_fr * 0.37 + 2 * self.fire_ph)
        v = on * fl * amt
        xi = (self.fire_xy[:, 0] / 2).astype(int); yi = (self.fire_xy[:, 1] / 2).astype(int)
        np.add.at(lay, (yi, xi), v)
        lay = cv2.GaussianBlur(lay, (0, 0), 2.0) * 25 + cv2.GaussianBlur(lay, (0, 0), 9.0) * 20
        return self.up(lay)[..., None] * np.array([1.0, 0.42, 0.08], f32)

    def shimmer(self, img, amp, t, y0, y1):
        if amp <= 0: return img
        u = (self.xx * 0.12) % 256; v = (self.yy * 0.12 + t * 14) % 256
        n = cv2.remap(self.shim, u.astype(f32), v.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        k = smooth(y0, y1, self.yy) * (1 - smooth(self.hz + 30, self.hz + 300, self.yy) * 0.7) * amp
        return cv2.remap(img, (self.xx + n * k).astype(f32), (self.yy + n * k * 0.6).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    def ring(self, img, C, u, R1, I=2.0, life=0.55):
        if u < 0 or u > 1.6: return
        R = R1 * (u / 1.6) ** 0.6; wdt = 18 + 60 * u
        dd = np.sqrt((self.xx - C[0]) ** 2 + (self.yy - C[1]) ** 2)
        for ch, off in ((0, 12), (1, 0), (2, -12)):
            img[..., ch] += np.exp(-((dd - R - off) / wdt) ** 2) * I * math.exp(-u / life)

    def dust_wall(self, t):
        """rolling dust front: rises from the horizon (T_BL0) and engulfs the view (T_HITS); half-res (alpha, rgb)"""
        u = (t - T_BL0) / (T_HITS - T_BL0)
        if u < 0: return None
        hz2 = self.hz / 2; hh = self.hx.shape[0]
        top = hz2 - (hz2 + 120) * (min(u, 1.15) ** 2.2)                          # top edge climbs to the frame top
        n = sample(self.N1, self.hx * 0.35 + t * 40, self.hy * 0.25 - t * 30) * 0.6 + sample(self.N2, self.hx * 0.9 - t * 90, self.hy * 0.8) * 0.4
        edge = top + 55 * self.k * n + 35 * np.sin(self.hx / 90 + t * 2)
        a = smooth(edge - 25, edge + 70, self.hy) * np.clip(0.75 + 0.25 * n, 0.3, 1)
        a = a * (0.85 + 0.15 * min(u, 1))
        lit = np.exp(-np.clip(self.hy - edge, 0, 400) / 80)[..., None]
        rgb = np.array([0.20, 0.11, 0.06], f32) * (0.7 + 0.3 * n[..., None]) + lit * np.array([0.9, 0.32, 0.08], f32) * 0.6
        return a.astype(f32), rgb.astype(f32)

    # -------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        L = self.L; W, H = L.W, L.H; fg = self.fg
        P = look(t)
        pulse = 1 + 0.10 * math.sin(2 * math.pi * t / 1.6) + sum(0.5 * math.exp(-((t - tp) / 0.20) ** 2) for tp in PULSES)
        tau = t - T_IMP
        zen = np.array(P["zen"], f32); hor = np.array(P["hor"], f32)
        sky = zen * (1 - self.k_hor) + hor * self.k_hor
        # sun aureole (+ dim red sun through the soot)
        sdx = self.hx - self.SUN[0]; sdy = self.hy - self.SUN[1]; sd = np.sqrt(sdx * sdx + sdy * sdy)
        winter = ramp(t, T_SOOT, T_SOOT + 1.2) * (1 - ramp(t, T_BACK - 0.12, T_BACK))
        suncol = np.array([1.0, 0.92, 0.80], f32) * (1 - winter) + np.array([1.0, 0.28, 0.08], f32) * winter
        sky = sky + (np.exp(-sd / 45) * 0.9 + np.exp(-sd / 220) * 0.12)[..., None] * suncol * (P["sunI"] + 0.25 * winter)
        if P["beams"] > 0.01: sky = sky + self.beams_layer(t, self.SUN, None) * P["beams"]
        # fireball glow along the horizon + coloured beams from the impact
        if tau > -0.05:
            gI = kf(tau, [(0, 0), (0.15, 1.8), (2.5, 0.9), (10, 0.6), (18, 0.4), (30, 0.2)]) * (1 - ramp(t, T_HITS, T_SOOT + 1))
            idx_ = self.hx - self.IMP[0]; idy = self.hy - self.IMP[1]; idd = np.sqrt(idx_ * idx_ * 0.35 + idy * idy)
            sky = sky + (np.exp(-idd / (260 * self.k)) * 0.9 + np.exp(-idd / (900 * self.k)) * 0.25)[..., None] * np.array([1.0, 0.45, 0.12], f32) * gI
            bI = kf(tau, [(0, 0), (0.2, 1.6), (3, 1.0), (9, 0.55), (T_EJ0 - T_IMP, 0.35), (T_HITS - T_IMP, 0.0)])
            if bI > 0.01:
                cols = [(1.0, 0.55, 0.08), (1.0, 0.85, 0.3), (1.0, 0.2, 0.35), (0.9, 0.35, 0.05), (1.0, 0.95, 0.6)]
                sky = sky + self.beams_layer(t, (self.IMP[0], self.IMP[1] - 120 * self.k), cols, reach=1300, wmul=0.8) * bI * 1.3
        # red-hot sky glow during the ejecta rain (flickering)
        redI = ramp(t, T_EJ0, T_RED + 0.5) * (1 - ramp(t, T_HITS, T_SOOT + 0.5))
        if redI > 0:
            fl = 1 + 0.12 * noise1(t, 3, 6.0)
            n = sample(self.N3, self.hx * 0.25 + t * 15, self.hy * 0.25 + t * 8)
            sky = sky + (np.array([0.30, 0.045, 0.012], f32) * (0.75 + 0.35 * n[..., None]) * (0.5 + 0.5 * self.el[..., None] ** 0.5)) * redI * fl
        if winter > 0:
            n = sample(self.N1, self.hx * 0.18 + t * 22, self.hy * 0.30 + t * 4) * 0.7 + sample(self.N2, self.hx * 0.35 - t * 30, self.hy * 0.5) * 0.3
            sky = sky * (1 + winter * (0.38 * n[..., None] - 0.05 * (1 - self.el[..., None])))
        # plume
        sky_amb = tuple(0.5 * a + 0.5 * b for a, b in zip(P["zen"], P["hor"]))
        flash = 30 * math.exp(-max(tau, 0) / 0.05) * ease((tau + 0.04) / 0.04) + 0.25 * math.exp(-max(tau, 0) / 0.8) + \
            0.8 * math.exp(-((t - T_FLASHW) / 0.22) ** 2) if tau > -0.05 else 0.0
        img = self.up(sky)
        # sun disc (white -> dim red in the winter)
        sI = (P["sunI"] * 40 + winter * 5)
        splat(img, self.SUN[0], self.SUN[1], 60, lambda d, dx, dy: (smooth(9.5, 8.0, d) * sI + np.exp(-d / 14) * sI * 0.06)[..., None] * suncol)
        ast, alight = self.asteroid(t)
        if ast is not None: img += self.up(ast)
        pl = self.plume(t, sky_amb, flash)
        if pl is not None:
            (x0, y0, x1, y1), col, al = pl
            X0, Y0, X1, Y1 = x0 * 2, y0 * 2, x1 * 2, y1 * 2
            colf = cv2.resize(col, (X1 - X0, Y1 - Y0), interpolation=cv2.INTER_LINEAR)
            alf = cv2.resize(al, (X1 - X0, Y1 - Y0), interpolation=cv2.INTER_LINEAR)[..., None]
            fade = 1 - ramp(t, T_HITS - 0.3, T_SOOT + 0.8)
            alf = alf * fade
            reg = img[Y0:Y1, X0:X1]
            img[Y0:Y1, X0:X1] = reg * (1 - alf) + colf * alf
        metI = ramp(t, T_EJ0, T_EJ0 + 1.0) * (1 - ramp(t, T_HITS - 0.2, T_HITS + 0.5))
        if metI > 0: img += self.up(self.meteors(t, metI * 2.6))
        dw = self.dust_wall(t) if T_BL0 <= t < T_SOOT + 2 else None
        if dw is not None and t < T_HITS:                                         # behind the park while it is far
            a_, rgb_ = dw; a_ = self.up(a_)[..., None]; img = img * (1 - a_) + self.up(rgb_) * a_
        # ---- foreground
        lightcol = (1.0, 0.95, 0.85)
        light = 1.0 + 0.10 * (pulse - 1) + alight * 0.8
        rimI = alight * 0.5
        if tau > 0:
            fI = kf(tau, [(0, 2.2), (0.4, 1.2), (3, 0.6), (10, 0.35), (T_EJ0 - T_IMP, 0.2), (T_HITS - T_IMP, 0.0)])
            rimI += fI; lightcol = (1.0, 0.62, 0.28)
        if redI > 0: rimI += 0.45 * redI * (1 + 0.15 * noise1(t, 5, 8.0)); lightcol = (1.0, 0.42, 0.12)
        fgc = self.relight(P, light, lightcol, rimI)
        fa = fg.a
        # wind sway after the blast hits (foliage only)
        sway = ramp(t, T_HITS - 0.1, T_HITS + 0.3) * (1 - 0.6 * ramp(t, T_HITS + 1.5, T_SOOT + 2.0)) * (1 - ramp(t, T_WO0, T_BACK))
        if sway > 0:
            n = sample(self.N1, self.xx * 0.02 + t * 3.0, self.yy * 0.06 + t * 1.2)
            hgt = np.clip((self.hz + 80 - self.yy) / 600, 0, 1) * (1 - fg.ground)
            dxm = (n * 6 + 8) * sway * hgt * self.k ** 0.5
            fgc = cv2.remap(fgc, (self.xx - dxm).astype(f32), self.yy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            fa = cv2.remap(fa, (self.xx - dxm).astype(f32), self.yy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        fireA = ramp(t, T_FIRE, T_FIRE + 1.5) * (1 - ramp(t, T_HITS - 0.2, T_HITS + 0.8))
        fs = self.fire_spots(t, fireA)
        if fs is not None: fgc = fgc + fs * fa[..., None]
        a = fa[..., None]
        img = img * (1 - a) + fgc * a
        # smoke from trees and grass, embers
        smA = ramp(t, T_FIRE - 0.3, T_FIRE + 1.2) * (1 - ramp(t, T_HITS - 0.2, T_HITS + 0.4))
        sm, smc = self.smoke(t, smA * 0.85, (0.035, 0.026, 0.022), 0.25)
        if sm is not None: img = img * (1 - sm[..., None]) + smc * sm[..., None]
        emA = ramp(t, T_RED, T_FIRE + 1.0) * (1 - ramp(t, T_HITS + 0.6, T_SOOT + 1.5))
        if emA > 0: img += self.embers(t, emA, wind=ramp(t, T_HITS - 0.1, T_HITS + 0.3))
        if dw is not None and t >= T_HITS:                                       # engulfs everything, thins to a haze
            a_, rgb_ = dw
            th = 1 - 0.90 * ramp(t, T_HITS + 0.4, T_SOOT + 1.5)
            a_ = self.up(cv2.GaussianBlur(a_, (0, 0), 1 + 10 * ramp(t, T_HITS, T_SOOT + 1)) * th)[..., None]; img = img * (1 - a_) + self.up(rgb_) * a_
        # dust motes streaming sideways
        moA = ramp(t, T_HITS - 0.3, T_HITS + 0.2) * (1 - ramp(t, T_SOOT + 0.5, T_SOOT + 2.5))
        if moA > 0:
            m = self.mote; lay = np.zeros((H // 2, W // 2), f32)
            for s in range(4):
                x = ((m["x"] + m["sp"] * (t - 0.012 * s)) % (W + 200) - 100) / 2
                xi = np.clip(x.astype(int), 0, W // 2 - 1); yi = np.clip((m["y"] / 2).astype(int), 0, H // 2 - 1)
                np.add.at(lay, (yi, xi), m["sz"] * moA * (1 - s / 4))
            lay = cv2.GaussianBlur(lay, (0, 0), 1.0) * 1.0
            img += self.up(lay)[..., None] * np.array([0.9, 0.55, 0.3], f32)
        # winter ash
        asA = ramp(t, T_SOOT, T_SOOT + 1.0) * (1 - ramp(t, T_WO0, T_BACK))
        if asA > 0: img += self.ash_layer(t, asA * 0.55)[..., None] * np.array([0.85, 0.80, 0.78], f32)
        # quake dust kicked up from the ground
        qd = math.exp(-max(t - T_JOLT, 0) / 1.4) * (t > T_JOLT - 0.05) * (1 - ramp(t, T_EJ0, T_EJ0 + 1)) * 0.55
        if qd > 0.01:
            n = sample(self.mist, self.hx * 0.5 + t * 20, self.hy * 0.5 + t * 50)
            band = smooth(self.hz / 2 - 140, self.hz / 2 + 10, self.hy) * (1 - smooth(self.hz / 2 + 80, self.hz / 2 + 400, self.hy) * 0.6)
            dmask = self.up(np.clip(n * 1.4 - 0.3, 0, 1) * band * qd)[..., None]
            img = img * (1 - dmask * 0.6) + dmask * 0.6 * np.array([0.55, 0.30, 0.15], f32)
        # heat distortion near the plume and the burning park
        sh_amp = 3.5 * math.exp(-max(tau, 0) / 6) * (tau > 0) + 2.5 * fireA
        if sh_amp > 0.05: img = self.shimmer(img, sh_amp, t, self.hz - 900 * self.k, self.hz - 20)
        # ---- flash + chromatic shockwaves
        if tau > -0.05: img += flash * np.array([1.0, 0.96, 0.88], f32)
        self.ring(img, self.IMP, tau, 2600 * self.k + 600, 2.2)
        self.ring(img, self.IMP, (t - T_JOLT), 2200 * self.k + 500, 0.9)
        self.ring(img, (W / 2, self.hz), (t - T_HITS), 2600, 1.6)
        # golden white-out -> back to the sunny park
        if T_WO0 < t < T_BACK + 0.6:
            v = ease((t - T_WO0) / (T_BACK - T_WO0)) if t < T_BACK else 1 - ease((t - T_BACK) / 0.6)
            img = img + (22 * v ** 2.5) * np.array([1.0, 0.88, 0.70], f32)
        # ---- camera-locked ground jolt: a few frames of shake (the ground itself moves)
        shake = 0.0
        for tj, amp in ((T_JOLT, 26.0), (T_JOLT2, 12.0), (T_HITS, 14.0)):
            u = t - tj
            if -0.02 < u < 1.2: shake += amp * math.exp(-max(u, 0) / 0.28)
        if shake > 0.3:
            dx = shake * noise1(t, 7, 14.0, 2) * self.k ** 0.5; dy = shake * noise1(t, 8, 17.0, 2) * 1.2 * self.k ** 0.5
            M = np.float32([[1.02, 0, -0.01 * W + dx], [0, 1.02, -0.01 * H + dy]])
            img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        img = self.chroma_bloom(img, 1.0)
        out = tonemap(img, P["expo"])
        out = self.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.16)
        self.overlay(out, t)
        return out

    def chroma_bloom(self, img, amt):
        img = bloom(img, 0.85 * amt)
        H, W = img.shape[:2]
        sm = cv2.resize(img, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
        sm = np.maximum(sm - 1.0, 0)
        acc = np.empty_like(sm)
        for c, s in ((0, 26), (1, 20), (2, 15)):
            acc[..., c] = cv2.GaussianBlur(sm[..., c], (0, 0), s)
        return img + cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR) * 0.35 * amt

    def chroma(self, out):
        W, H = self.L.W, self.L.H
        o = out.copy()
        for ch, k in ((0, 1.0018), (2, 0.9982)):
            M = np.float32([[k, 0, (1 - k) * W / 2], [0, k, (1 - k) * H / 2]])
            o[..., ch] = cv2.warpAffine(out[..., ch], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return o

    # -------------------------------------------------------------------------------------------- text
    READOUTS = None

    def readouts(self):
        if self.READOUTS: return self.READOUTS
        ORG = (255, 150, 40); RED = (255, 95, 60); ICE = (230, 225, 220); GRN = (150, 235, 120)
        R = [
            (0.35, LN["hook"]["end"] - 0.05, "CHICXULUB IMPACT", ORG, "66 MILLION YEARS AGO", "YOU: ~1,000 KM AWAY"),
            (LN["appr"]["start"] + 0.1, T_IMP - 0.25, "ASTEROID", (255, 235, 190), "~10 KM WIDE", "~20 KM/S · 72,000 KM/H"),
            (T_IMP + 0.9, LN["hit"]["end"] + 0.1, "BRIGHTER THAN THE SUN", (255, 240, 200), "~100 MILLION MEGATONS", "BILLIONS OF HIROSHIMAS"),
            (T_Q0 + 0.1, LN["quake"]["end"] + 0.1, "MEGAQUAKE", ORG, "MAGNITUDE ~10–11", "SEISMIC WAVES ARRIVE IN MINUTES"),
            (LN["ejecta"]["start"] + 0.1, LN["ejecta"]["end"] + 0.1, "EJECTA RE-ENTRY", RED, "MOLTEN ROCK SPHERULES", "THE SKY GLOWS FOR HOURS"),
            (T_BL0 + 0.1, T_SOOT - 0.1, "AIR BLAST", ORG, "ARRIVES ~1 HOUR LATER", "SOUND TRAVELS SLOWER THAN LIGHT"),
            (T_SOOT + 0.1, T_75 - 0.1, "IMPACT WINTER", ICE, "MONTHS TO YEARS", "SOOT + SULFATE BLOCK THE SUN"),
            (T_75, LN["blast"]["end"] + 0.3, "~75% OF SPECIES", RED, "GONE", "INCLUDING NON-BIRD DINOSAURS"),
            (T_BACK + 0.45, DUR + 1, "66 MILLION YEARS LATER", GRN, "MAMMALS TOOK OVER", "INCLUDING US"),
        ]
        self.READOUTS = R; return R

    def counter(self, t):
        if t < T_IMP - 5.0 or t > DUR: return None
        if t < T_IMP: return f"T−{max(0, math.ceil(T_IMP - t)):d} S"
        if t < T_Q0: return f"T+{int(90 * (t - T_IMP) / (T_Q0 - T_IMP)):d} S"
        if t < LN["quake"]["end"] + 0.2: return f"T+{1 + int(7 * (t - T_Q0) / (LN['quake']['end'] + 0.2 - T_Q0)):d} MIN"
        if t < T_BL0: return f"T+{10 + int(35 * (t - T_EJ0) / (T_BL0 - T_EJ0)):d} MIN" if t > T_EJ0 else "T+10 MIN"
        if t < T_HITS: return f"T+{45 + int(15 * (t - T_BL0) / (T_HITS - T_BL0)):d} MIN"
        if t < T_SOOT: return "T+1 HOUR"
        if t < LN["blast"]["end"] + 0.3:
            mo = 1 + int(23 * ramp(t, T_SOOT, T_75 + 1.0))
            return f"T+{mo} MONTH" + ("S" if mo > 1 else "") if mo < 12 else f"T+{mo // 12} YEAR" + ("S" if mo >= 24 else "")
        if t < T_BACK: return None
        return "T+66,000,000 YEARS"

    def overlay(self, out, t):
        L = self.L; W = L.W
        if L.vertical: x, ys = W / 2, (1205, 1290, 1350)
        else: x, ys = 470, (800, 875, 930)
        for t0, t1, name, tc, l2, l3 in self.readouts():
            a = ramp(t, t0, t0 + 0.3) * (1 - ramp(t, t1 - 0.2, t1))
            if a > 0.01:
                dy = (1 - a) * 18
                big = int(L.hud_size * (1.45 if len(name) < 12 else 1.12))
                rgba, _ = word_layer(name, big, W * 0.9 if L.vertical else 820, fill=tc)
                composite(out, rgba, x, ys[0] + dy, a)
                hud_text(out, l2, x, ys[1] + dy, int(L.hud_size * 0.62), "Black", (255, 255, 255), a, 0.08, display=True)
                hud_text(out, l3, x, ys[2] + dy, int(L.hud_size * 0.48), "Bold", (240, 238, 232), a, 0.10, display=True)
        c = self.counter(t)
        if c:
            a = ramp(t, T_IMP - 5.0, T_IMP - 4.7)
            if t > T_BACK: a = ramp(t, T_BACK + 0.45, T_BACK + 0.75)
            cy = 255 if L.vertical else 70
            hud_text(out, c, W / 2, cy, int(L.hud_size * 0.95), "Black", (255, 255, 255), a, 0.06, display=True)
        self.caps.draw(out, t)


def run(vertical, stills=None):
    sc = Scene(vertical); tag = "vert" if vertical else "wide"
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


def patch(vertical, ranges):
    """re-render only frames inside `ranges` [(t0, t1)], copying the others from the existing render"""
    import subprocess
    sc = Scene(vertical); tag = "vert" if vertical else "wide"
    W, H = sc.L.W, sc.L.H; src = os.path.join(SCR, f"video_{tag}.mp4"); old = src.replace(".mp4", "_prev.mp4")
    os.replace(src, old)
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", old, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = Encoder(src, W, H, FPS, crf=16)
    for i in range(int(round(DUR * FPS))):
        buf = dec.stdout.read(W * H * 3); t = i / FPS
        if any(a <= t <= b for a, b in ranges) or len(buf) < W * H * 3: enc.write(sc.frame(t))
        else: enc.p.stdin.write(buf)
    enc.close(); dec.wait(); os.remove(old); print("patched")


if __name__ == "__main__":
    if sys.argv[1] == "info":
        print("DUR", DUR, {k: round(v, 2) for k, v in dict(T_STAR=T_STAR, T_ENTRY=T_ENTRY, T_IMP=T_IMP, T_FLASHW=T_FLASHW, T_JOLT=T_JOLT,
              T_EJ0=T_EJ0, T_RED=T_RED, T_FIRE=T_FIRE, T_BL0=T_BL0, T_HITS=T_HITS, T_SOOT=T_SOOT, T_75=T_75, T_WO0=T_WO0, T_BACK=T_BACK).items()})
        sys.exit()
    if sys.argv[1] == "patch":
        patch(sys.argv[2] != "wide", [tuple(float(v) for v in r.split(":")) for r in sys.argv[3].split(",")]); sys.exit()
    vert = sys.argv[1] != "wide"
    st = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    run(vert, st)
