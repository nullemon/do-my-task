"""WHAT IF EARTH HAD RINGS LIKE SATURN? -- one locked tripod shot of the valley (B_valley), VFX spectacle style.
Saturn-like rings in Earth's equatorial plane, physically projected for each latitude through a locked stereographic
sky lens (rings.py). Beats (sky changes, the valley stays):
  hook  golden hour, no rings -> FLASH, the rings unfurl from the horizon (New York, 41 N, winter morning)
  ny    vast arch over the southern sky, unlit face glowing by forward scattering, ring shadows banding the land
  night midnight (summer): ring-lit silver valley, Earth's shadow slicing the arch, stars, meteors
  eq    equator, noon: rings edge-on, a razor-thin line from the horizon straight up through the zenith (facing east)
  oslo  60 N midsummer night: a low massive band along the southern horizon, Earth's shadow on its lower part
  end   flash back to our ringless golden sky; a ghost of the Ordovician ring fades (loops to frame 0)
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py vert|wide              full render -> SCR/video_<tag>.mp4
  /home/user/ttsenv/bin/python short.py vert 1.0,9.5           stills -> SCR/stills/<tag>_<t>.png
  /home/user/ttsenv/bin/python short.py patch vert 3.9:5.2     re-render only those time ranges
  /home/user/ttsenv/bin/python short.py info                   timeline + geometry facts
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), os.path.join(HERE, "audio"), HERE]
import lib.core  # noqa: F401  (sets up pylib path)
import numpy as np, cv2
from PIL import Image
from lib.core import f32, Layout, ramp, smooth, ease, noise1, lum, fbm2, bbcolor
from lib.foreground import Foreground
from lib.sky import SkyCam, StarSky
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish, Encoder
from lib.audio import place
import rings as RG

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S7-earth-rings"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/B_valley.png"
FPS = 30
LEAD, TAIL = 0.25, 1.45

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]


# ------------------------------------------------------------------------------------------------ beats
# geo: (latitude, camera azimuth). sun: (declination, hour angle start, hour angle end) -- time-lapse within the beat.
# sky: zenith / horizon colours (linear), sun-glow colour, anti-sun belt, star gain, ring gain K, ring sky-glow, exposure.
BEATS = {
    "ny":    dict(geo=(41.0, 180.0), sun=(-8.5, -76.0, -68.0), K=16.0, glow=0.05, expo=1.0, tint=(1.40, 0.84, 0.46), gt=0.10,
                  zen=(0.010, 0.085, 0.55), hor=(1.35, 0.55, 0.17), sg=(2.6, 1.0, 0.25), belt=(0.30, 0.10, 0.30), stars=0.0,
                  name="NEW YORK · 41° N", l2="RINGS 7,000–80,000 KM OUT", l3="WINTER · GOLDEN HOUR", tc=(255, 196, 120)),
    "night": dict(geo=(41.0, 180.0), sun=(20.0, 140.0, 168.0), K=5.5, glow=0.10, expo=1.25, tint=(0.92, 0.98, 1.08),
                  zen=(0.010, 0.030, 0.120), hor=(0.030, 0.060, 0.150), sg=(0.0, 0.0, 0.0), belt=(0, 0, 0), stars=1.0,
                  name="NEW YORK · MIDNIGHT", l2="RINGLIGHT ≈ 1,000s × FULL MOON", l3="EARTH'S SHADOW ON THE RINGS", tc=(170, 210, 255)),
    "eq":    dict(geo=(0.05, 90.0), sun=(6.0, -9.0, 7.0), K=10.0, glow=0.20, expo=0.95, tint=(1.0, 1.0, 1.0),
                  zen=(0.020, 0.140, 0.78), hor=(0.50, 0.68, 1.00), sg=(1.0, 0.95, 0.85), belt=(0, 0, 0), stars=0.0,
                  name="EQUATOR · 0°", l2="RINGS SEEN EDGE-ON", l3="NOON", tc=(130, 230, 255)),
    "oslo":  dict(geo=(60.0, 180.0), sun=(21.0, 146.0, 153.0), K=7.0, glow=0.20, expo=1.25, tint=(1.12, 0.86, 0.86),
                  zen=(0.030, 0.035, 0.170), hor=(0.50, 0.20, 0.32), sg=(0.9, 0.35, 0.25), belt=(0.35, 0.12, 0.30), stars=0.35,
                  name="OSLO · 60° N", l2="ARCH ONLY 17° HIGH", l3="MIDSUMMER NIGHT", tc=(255, 150, 200)),
}
BEATS["end"] = dict(BEATS["ny"], sun=(-8.5, -79.0, -76.0), name="", l2="", l3="")
ORDER = ["ny", "night", "eq", "oslo", "end"]
T_RINGS = wt("hook", "RINGS") - 0.03
T_SW = {k: LN[k]["start"] - 0.06 for k in ("night", "eq", "oslo", "end")}
STARTS = {"ny": 0.0, **T_SW}
ENDS = {"ny": T_SW["night"], "night": T_SW["eq"], "eq": T_SW["oslo"], "oslo": T_SW["end"], "end": DUR}
SWAPS = [(T_RINGS, "ny")] + [(T_SW[k], k) for k in ("night", "eq", "oslo", "end")]
PULSES = [wt("ny", "VAST"), wt("ny", "ARCH"), wt("ny", "SHADOWS"), wt("night", "OUTSHINE"), wt("night", "SHADOW"),
          wt("eq", "RAZOR-THIN"), wt("eq", "OVERHEAD"), wt("oslo", "GIANT"), wt("oslo", "WALL"), wt("end", "466 MILLION")]
T_STRIPE = wt("ny", "STRIPING")
T_SLICE = wt("night", "SLICES")


def beat_at(t):
    cur = "ny"
    for k in ORDER:
        if t >= STARTS[k]: cur = k
    return cur


def lerp(a, b, w): return tuple(x + (y - x) * w for x, y in zip(a, b)) if isinstance(a, tuple) else a + (b - a) * w


def sun_of(key, t):
    B = BEATS[key]; dec, h0, h1 = B["sun"]
    u = (t - STARTS[key]) / max(ENDS[key] - STARTS[key], 1e-3)
    if key == "ny": u = t / ENDS["ny"]
    return RG.sun_vec(dec, h0 + (h1 - h0) * min(max(u, 0), 1))


def palette(x):
    x = x[..., None] if np.ndim(x) else x
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (x - np.array([0.0, 0.33, 0.67], f32)))
    return (c ** 2.2).astype(f32)


# ------------------------------------------------------------------------------------------------ scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(vertical); W, H = L.W, L.H; self.vertical = vertical
        self.fg = fg = Foreground(FG_PATH, L, lamps=[], hz_frac=0.72)
        self.hz = hz = float(fg.horizon)
        self.f = 880.0 if vertical else 640.0
        # cylindrical sky lens (px per radian): vertical +-72 deg wide, ~93 deg tall (zenith in frame); 16:9 +-85 deg wide, ~62 deg tall
        self.lens = (540 / math.radians(72), 860.0) if vertical else (960 / math.radians(85), (hz) / math.radians(62))
        self.C = (540.0, 760.0) if vertical else (960.0, 330.0)                     # shockwave centre (arch apex area)
        self.prof = RG.Profile()
        self.geos = {}
        for k in ("ny", "night", "eq", "oslo"):
            g = BEATS[k]["geo"]
            if g not in self.geos: self.geos[g] = RG.Geo(self.prof, W, H, hz, self.f, g[1], g[0], lens=self.lens)
        self.cam = SkyCam(W, H, hz, self.f)
        self.stars = StarSky()
        yyf, xxf = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xxf, yyf
        hw, hh = W // 2, H // 2
        # foreground prep: skyline rim, ground distance proxy (km) for the ring-shadow bands
        a = fg.a
        sh = np.zeros_like(a); sh[10:] = a[:-10]
        self.rim = cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 3.0) * a
        self.rim_soft = cv2.GaussianBlur(np.clip(a - np.roll(a, 40, 0), 0, 1), (0, 0), 14.0) * a
        dy = np.maximum(yyf - hz + 14 * fg.s, 3.0)
        self.gdist = (26.0 * (14 * fg.s / dy) ** 0.45).astype(f32)                    # far ridges ~26 km -> a few km in front (softened)
        self.gx = ((xxf - W / 2) / W).astype(f32)
        ny_ = np.random.default_rng(4)
        self.bandn = cv2.resize(fbm2((64, 64), 77, 2.4), (W, H), interpolation=cv2.INTER_CUBIC).astype(f32)
        # spokes noise (radius band x longitude)
        self.spk = fbm2((32, 512), 55, 1.6)
        # meteors (night): ring debris burning up
        r = np.random.default_rng(12); nm = 14
        self.met = [dict(t0=r.uniform(0, 1), x=r.uniform(0.1, 0.9), y=r.uniform(0.05, 0.45), a=r.uniform(-2.6, -0.5), L=r.uniform(120, 320),
                         b=r.uniform(0.5, 1.4)) for _ in range(nm)]
        emph = {"RINGS", "SATURN", "VAST", "ARCH", "SHADOWS", "OUTSHINE", "MOON", "SHADOW", "SLICES", "EQUATOR", "RAZOR-THIN",
                "OVERHEAD", "OSLO", "GIANT", "WALL", "466 MILLION", "ONCE", "NEW", "YORK"}
        self.caps = Captions(L, WORDS, emphasis=emph)
        L.cap_y = 1010 if vertical else 610
        self.tau_ground_cache = {}

    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    # -------------------------------------------------------------------------------------------- sky
    def sky(self, geo, sv, A, B, w, t):
        dh = geo.dh; alt = np.maximum(geo.alt_h, 0) / 57.3
        zen = np.array(lerp(A["zen"], B["zen"], w), f32); hor = np.array(lerp(A["hor"], B["hor"], w), f32)
        sg = np.array(lerp(A["sg"], B["sg"], w), f32); belt = np.array(lerp(A["belt"], B["belt"], w), f32)
        c = np.clip(dh @ sv.astype(f32), -1, 1); gam = np.arccos(c)
        k = np.exp(-alt / 0.22)[..., None]
        sky = zen * (1 - k) + hor * k
        sky = sky * (0.80 + 0.20 * (1 + c * c)[..., None] / 2)
        sun_alt = math.degrees(math.asin(float(sv @ geo.U)))
        lit = smooth(-8.0, 2.0, sun_alt)
        glow = (np.exp(-gam / 0.10) * 1.6 + np.exp(-gam / 0.35) * 0.45 + np.exp(-gam / 1.0) * 0.12) * (0.4 + 0.6 * np.exp(-alt / 0.35))
        sky = sky + glow[..., None] * sg * lit
        # anti-sun belt (Belt of Venus) a few degrees above the horizon, opposite the sun
        anti = np.clip(-c, 0, 1) ** 2
        sky = sky + (np.exp(-((alt - 0.12) / 0.08) ** 2) * (0.4 + 0.6 * anti))[..., None] * belt
        return sky

    # -------------------------------------------------------------------------------------------- rings
    def ring_layer(self, geo, sv, K, t, vis_r, edge_r, gain=1.0, tint=(1, 1, 1), gt=0.0):
        """-> (rgb radiance at ring pixels, transmission T, glow image small) at the masked pixels of geo"""
        I, sh, fringe = geo.shade(sv, glowthick=gt)
        # spokes / orbital texture (Keplerian shear, time-lapse)
        om = 0.9 * (geo.r / 12000.0) ** -1.5
        lam = (geo.lam - om * t * 0.25) % (2 * np.pi)
        ri = np.clip((geo.r - 9500) / (28000 - 9500) * 31, 0, 31).astype(np.int32)
        sp = self.spk[ri, (lam / (2 * np.pi) * 511).astype(np.int32)]
        tex = 1 + 0.10 * sp * ((geo.r > 9500) & (geo.r < 19000))
        L = (K * gain) * (I * sh * tex)[:, None] * geo.alb * np.array(tint, f32)
        L += (fringe * 0.015 * K * gain)[:, None] * np.array([1.0, 0.30, 0.08], f32) * (1 - np.exp(-geo.tau / geo.mu))[:, None]
        # reveal: rings unfurl outward from the inner edge, bright leading edge
        if vis_r is not None:
            v = smooth(vis_r, vis_r - 1800, geo.r).astype(f32)
            L = L * v[:, None]
            if edge_r is not None:
                e = np.exp(-((geo.r - edge_r) / 900.0) ** 2).astype(f32) * (geo.tau > 0.005)
                L += (e * 6.0)[:, None] * palette(geo.r / 9000.0 - t * 0.8) * 0.8 + (e * 3.0)[:, None]
        else:
            v = 1.0
        T = 1 - (1 - geo.T) * v
        L = L * geo.ext
        return L, T

    def ground_shadow(self, geo, sv, t, key):
        """ring-shadow transmission over the land (banding where sunlight passes through the rings)"""
        O = geo.O
        if sv[2] * O[2] >= 0 or abs(sv[2]) < 1e-3: return None
        s0 = -O[2] / sv[2]; Q = O + s0 * sv; rq = float(np.hypot(Q[0], Q[1]))
        sweep = 1.0 + 0.9 * ramp(t, T_STRIPE - 0.4, T_STRIPE + 0.8)
        rr = rq - (self.gdist * (1.0 + 0.30 * self.gx + 0.06 * self.bandn) + self.bandn * 0.35) * 110.0 * sweep + 250 + (t - STARTS[key]) * 30.0
        sm = cv2.resize(rr, (self.L.W // 4, self.L.H // 4), interpolation=cv2.INTER_AREA)
        tau = self.prof.tau_soft(sm.ravel().astype(np.float64), 2.0).reshape(sm.shape)
        Tr = cv2.GaussianBlur((np.exp(-tau / max(abs(float(sv[2])), 0.05)) ** 0.8).astype(f32), (0, 0), 1.5)
        return cv2.resize(Tr.astype(f32), (self.L.W, self.L.H), interpolation=cv2.INTER_CUBIC)

    # -------------------------------------------------------------------------------------------- foreground
    def relight(self, key, t, S, ringE):
        fg = self.fg
        if key in ("ny", "end"):
            sun = fg.rgb * 1.06
            amb = fg.flat * np.array([0.050, 0.070, 0.120], f32)
            out = sun * (S[..., None] if S is not None else 1.0) + amb
            out += (self.rim * 0.5 + self.rim_soft * 0.15)[..., None] * np.array([1.0, 0.6, 0.3], f32) * 0.25
            return out
        if key == "night":
            y = lum(fg.flat)[..., None]
            base = fg.flat * 0.30 + y * 0.70
            out = base * np.array([0.60, 0.74, 1.0], f32) * (0.50 * ringE)
            out += (self.rim * 0.9 + self.rim_soft * 0.3)[..., None] * np.array([0.75, 0.85, 1.0], f32) * 0.30 * ringE
            return out
        if key == "eq":
            base = fg.rgb * 0.7 + fg.flat * 0.3
            y = lum(base)[..., None]
            base = y + (base - y) * 0.85
            out = base * np.array([0.80, 0.97, 1.22], f32) * 1.35
            if S is not None: out = out * (0.25 + 0.75 * S[..., None])
            return out + fg.flat * np.array([0.03, 0.05, 0.09], f32)
        if key == "oslo":
            out = fg.flat * np.array([0.26, 0.18, 0.32], f32) * (0.65 + 0.45 * ringE)
            out += (self.rim * 0.8 + self.rim_soft * 0.3)[..., None] * np.array([1.0, 0.62, 0.55], f32) * 0.25 * ringE
            return out
        return fg.rgb

    # -------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        L = self.L; W, H = L.W, L.H; fg = self.fg
        key = beat_at(t); B = BEATS[key]
        prev = ORDER[ORDER.index(key) - 1] if key != "ny" else "ny"
        ts = STARTS[key]
        w = ramp(t, ts - 0.10, ts + 0.45) if key != "ny" else 1.0
        A = BEATS[prev]
        geo = self.geos[B["geo"]]
        sv = sun_of(key, t)
        pulse = 1 + 0.06 * math.sin(2 * math.pi * t / 1.7) + sum(0.35 * math.exp(-((t - tp) / 0.22) ** 2) for tp in PULSES)
        # ---- sky (half res)
        skyh = self.sky(geo, sv, A, B, w, t)
        stars_g = lerp(A["stars"], B["stars"], w)
        # ---- rings
        rings_on = key not in ("end",) and not (key == "ny" and t < T_RINGS)
        nxt = [s for s, _ in SWAPS if s > t]; t_next = nxt[0] if nxt else 1e9
        surge = 1 + 2.2 * ramp(t, t_next - 0.35, t_next) if t_next < 1e8 else 1.0      # anticipation before each flash
        img = self.up(skyh)
        ringE = 0.0
        if rings_on:
            t_rev = T_RINGS if key == "ny" else ts
            u = (t - t_rev) / 0.85
            if u < 1.0:
                ue = ease(u) ** 0.9
                vis = RG.R0 * (RG.R1 * 1.05 / RG.R0) ** ue; edge = vis
            else: vis, edge = None, None
            Lr, T = self.ring_layer(geo, sv, B["K"], t, vis, edge, gain=pulse * surge, tint=B["tint"], gt=B.get("gt", 0.0))
            flat = img.reshape(-1, 3)
            if stars_g > 0:
                st = self.stars.render(self.cam, t, gain=1.0, plate_gain=0.45) * stars_g
                sf_ = st.reshape(-1, 3); sf_[geo.idx] *= T[:, None]
                img = img + st; flat = img.reshape(-1, 3)
            flat[geo.idx] += Lr
            # glints: ring particles catching the light
            gi = geo.glint
            if len(gi):
                tw = np.clip(np.sin(t * geo.glint_fr * 6.283 + geo.glint_ph), 0, 1) ** 14
                val = tw * np.minimum(lum(Lr[gi]), 3.0) * 1.6
                lay = np.zeros((H, W), f32); np.add.at(lay, (geo.ys[gi], geo.xs[gi]), val)
                lay = cv2.GaussianBlur(lay, (0, 0), 0.8) * 3 + cv2.GaussianBlur(lay, (0, 0), 2.2) * 1.2
                img += lay[..., None] * np.array([1.0, 0.95, 0.85], f32)
            # ring light scattered in the air (sky glow) + illuminance proxy for the ground
            sm = np.zeros((H // 8, W // 8, 3), f32)
            np.add.at(sm, (geo.ys // 8, geo.xs // 8), Lr / 64.0)
            ringE = float(sm.sum() / (sm.shape[0] * sm.shape[1]) / 3) * 12.0
            gl = cv2.GaussianBlur(sm, (0, 0), 9) * 0.8 + cv2.GaussianBlur(sm, (0, 0), 30) * 0.6
            img += self.up(gl) * B["glow"] * (1 - fg.a[..., None])
        else:
            if stars_g > 0: img += self.stars.render(self.cam, t, gain=1.0, plate_gain=0.45) * stars_g
        if key == "end":                                                         # ghost of the Ordovician ring
            gh = ramp(t, wt("end", "RINGS") - 0.2, wt("end", "RINGS") + 0.5) * (1 - ramp(t, wt("end", "YEARS"), ENDS["end"] - 0.5))
            if gh > 0.003:
                g0 = self.geos[(41.0, 180.0)]
                Lr, T = self.ring_layer(g0, sun_of("ny", 0.0), BEATS["ny"]["K"], t, None, None, gain=0.35 * gh, tint=BEATS["ny"]["tint"], gt=BEATS["ny"]["gt"])
                img.reshape(-1, 3)[g0.idx] += Lr * (0.75 + 0.25 * math.sin(t * 6.0))
        if key == "night":                                                       # meteors from ring debris
            img += self.meteors(t)
        # ---- foreground
        S = None
        if key in ("ny",) and rings_on: S = self.ground_shadow(geo, sv, t, key)
        if key == "ny" and S is not None: S = 1 - (1 - S) * ramp(t, T_RINGS + 0.3, T_RINGS + 1.2)
        if key == "eq":
            c = 28 - 34 * ((t - ts) / (ENDS["eq"] - ts)) ** 0.8                          # shadow of the ring edge sweeping in (km)
            band = np.exp(-((self.gdist - c) / (0.8 + 0.08 * self.gdist)) ** 2)
            S = (1 - 0.85 * band * ramp(t, ts + 0.6, ts + 1.4)).astype(f32)
        fgc = self.relight(key, t, S, ringE)
        if w < 1 and prev != key:
            fga = self.relight(prev, t, None, ringE if prev != "night" else 1.5)
            fgc = fga * (1 - w) + fgc * w
        a = fg.a[..., None]
        img = img * (1 - a) + fgc * a
        # ---- swap flash + chromatic shockwave
        for s_, k in SWAPS:
            u = t - s_
            if -0.05 < u < 1.4:
                fc = np.array({"ny": (1.0, 0.75, 0.45), "night": (0.6, 0.75, 1.0), "eq": (0.75, 0.95, 1.0), "oslo": (1.0, 0.6, 0.8),
                               "end": (1.0, 0.85, 0.6)}[k], f32)
                img += (3.2 * math.exp(-max(u, 0) / 0.08) * ease((u + 0.05) / 0.05)) * fc
                R = 2400 * (max(u, 0) / 1.4) ** 0.6; wdt = 18 + 60 * u
                dd = np.sqrt((self.xx - self.C[0]) ** 2 + (self.yy - self.C[1]) ** 2)
                for ch, off in ((0, 10), (1, 0), (2, -10)):
                    img[..., ch] += np.exp(-((dd - R - off) / wdt) ** 2) * 2.0 * math.exp(-max(u, 0) / 0.55)
        img = self.chroma_bloom(img, 1.0)
        expo = lerp(A["expo"], B["expo"], w)
        out = tonemap(img, expo)
        out = self.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.16)
        self.overlay(out, t, key)
        return out

    def meteors(self, t):
        W, H = self.L.W, self.L.H
        lay = np.zeros((H // 2, W // 2), f32)
        for i, m in enumerate(self.met):
            per = 2.3; ph = ((t / per) + m["t0"]) % 1.0
            if ph > 0.22: continue
            u = ph / 0.22
            x0, y0 = m["x"] * W, m["y"] * self.hz
            dx, dy = math.cos(m["a"]), -math.sin(m["a"])
            for k in range(24):
                s = (u - k * 0.012) * m["L"]
                if s < 0: break
                x, y = (x0 + dx * s) / 2, (y0 - dy * s * -1) / 2
                if 0 <= x < W // 2 and 0 <= y < H // 2:
                    lay[int(y), int(x)] += m["b"] * (1 - k / 24) ** 2 * math.sin(math.pi * u) * 3
        lay = cv2.GaussianBlur(lay, (0, 0), 0.7) * 3 + cv2.GaussianBlur(lay, (0, 0), 2.5)
        return self.up(lay)[..., None] * np.array([0.8, 0.95, 1.0], f32)

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

    def overlay(self, out, t, key):
        L = self.L; W = L.W
        S = BEATS[key]
        if L.vertical: x, ys = W / 2, (330, 415, 470)
        else: x, ys = W / 2, (95, 165, 215)
        t0 = T_RINGS + 0.5 if key == "ny" else STARTS[key]
        a = ramp(t, t0 + 0.15, t0 + 0.45)
        if key in ORDER[:-1]:
            nx = STARTS[ORDER[ORDER.index(key) + 1]]; a *= 1 - ramp(t, nx - 0.35, nx - 0.15)
        if a > 0.01 and S["name"]:
            dy = (1 - a) * 18
            big = int(L.hud_size * 1.30)
            rgba, _ = word_layer(S["name"], big, W * 0.92 if L.vertical else 1100, fill=S["tc"])
            composite(out, rgba, x, ys[0] + dy, a)
            if S["l2"]: hud_text(out, S["l2"], x, ys[1] + dy, int(L.hud_size * 0.60), "Black", (255, 255, 255), a, 0.08, display=True)
            if S["l3"]: hud_text(out, S["l3"], x, ys[2] + dy, int(L.hud_size * 0.46), "Bold", (235, 240, 250), a, 0.10, display=True)
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


def info():
    print("DUR", DUR, "rings", round(T_RINGS, 2), {k: round(v, 2) for k, v in T_SW.items()})
    for k in ("ny", "night", "eq", "oslo", "end"):
        B = BEATS[k]; phi = B["geo"][0]
        for tt in (STARTS[k] + 0.01, ENDS[k] - 0.01):
            al, az = RG.alt_az(sun_of(k, tt), phi)
            print(f"{k:6s} t={tt:5.2f} sun alt {al:6.1f} az {az:6.1f}")
    for phi in (41.0, 60.0):
        print(phi, "meridian ring altitude:", {r: round(RG.ring_alt_meridian(r, phi), 1) for r in (9500, 19000, 21500, 28000, 80000)},
              "visible above r =", round(RG.RE / math.cos(math.radians(phi))))


if __name__ == "__main__":
    if sys.argv[1] == "info": info(); sys.exit()
    if sys.argv[1] == "patch":
        patch(sys.argv[2] != "wide", [tuple(float(v) for v in r.split(":")) for r in sys.argv[3].split(",")]); sys.exit()
    vert = sys.argv[1] != "wide"
    st = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    run(vert, st)
