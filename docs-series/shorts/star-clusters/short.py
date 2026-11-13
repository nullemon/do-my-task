"""WHAT IF WE LIVED INSIDE A STAR CLUSTER? -- vertical Short (9:16 only).
LOCKED CAMERA: one tripod frame of the user's valley plate (B_valley.png) at night, facing south from 34 deg N.
  today     the real sky (HYG v4.1, V < 6.5) with the vivid Milky Way over a deep blue/violet night; the real Pleiades
            (M45) high in the south get a target ring
  swaps     flash + chromatic shockwave from the new cluster's core direction; the new sky is revealed inside the ring;
            coloured light beams from the core; readout NAME / STARS / BRIGHTER THAN SIRIUS / NEAREST STAR
  clusters  procedural populations from clusters.py (Pleiades, Hyades, Omega Centauri, the Milky Way's nuclear star
            cluster), every star at its computed apparent magnitude and colour; faint stars as integrated light; the
            valley relit by the combined starlight (blue / warm / golden), faint multiple star shadows
  end       white-out back to today's quiet sky (loops)
Built on docs-series/shorts/lib (read-only). Usage (one heavy process at a time, under nice):
  /home/user/ttsenv/bin/python short.py vert              full render -> SCR/video_vert.mp4
  /home/user/ttsenv/bin/python short.py vert 1.0,9.5      stills -> SCR/stills/vert_<t>.png
  /home/user/ttsenv/bin/python short.py info
"""
import os, sys, math, time, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (pylib path for cv2 / PIL)
import numpy as np, cv2
from PIL import Image
from lib.core import f32, Layout, ramp, smooth, ease, lum, fbm2, bbcolor, splat
from lib.foreground import Foreground
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish, Encoder
from lib.audio import place
from skygeo import eq_vec, eq2hor, lens_for, hdir, EQ2GAL
from mwsky import canvas, WL, HB, PXD

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B2-star-clusters"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/B_valley.png"
FPS = 30
LEAD, TAIL = 0.25, 1.15

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]

STATS = json.load(open(os.path.join(SCR, "stats.json")))

# ------------------------------------------------------------------------------------------------- timeline
T_SW = {k: LN[k]["start"] - 0.08 for k in ("ple", "hya", "ome", "nsc")}
T_BACK = LN["end"]["start"] - 0.05                       # white-out peak -> today's sky again
T_WO0 = T_BACK - 0.85
REVEAL = 1.0                                             # shockwave reveal time
L0 = 3.85                                                # sidereal time (h): the Pleiades near the meridian, high
RATE = 1.6 / 40.0                                        # sidereal drift (h per s): slow, constant motion


def LST(t):
    """drifts all the time; after the white-out it is re-based so that LST(DUR) == LST(0) (seamless loop)"""
    return L0 + RATE * (t if t < T_BACK else t - DUR)


SWAPS = [(T_SW["ple"], "pleiades"), (T_SW["hya"], "hyades"), (T_SW["ome"], "omega"), (T_SW["nsc"], "nsc"), (T_BACK, "today")]


def scene_at(t):
    cur, t0 = "today", -10.0
    for ts, k in SWAPS:
        if t >= ts: cur, t0 = k, ts
    prev = "today"
    for i, (ts, k) in enumerate(SWAPS):
        if ts == t0 and i > 0: prev = SWAPS[i - 1][1]
    nxt = [ts for ts, k in SWAPS if ts > t]
    return cur, prev, t0, (nxt[0] if nxt else 1e9)


def fmt(n): return f"{n:,}"


def bv_temp(ci):
    return 4600.0 * (1.0 / (0.92 * ci + 1.7) + 1.0 / (0.92 * ci + 0.62))


M45 = (56.75, 24.12)                                     # Pleiades centre (RA, Dec deg)
HYA = (66.75, 15.87)                                     # Hyades centre
st = STATS
SCN = {
    "today": dict(name="OUR SKY TODAY", l2="~5,000 NAKED-EYE STARS", sir=0, near="4.2 LY", tc=(150, 200, 255),
                  hyg=1.0, mw=1.0, cl=None, core=None, beams=None, bI=0.0, air=0.0, aircol=(0.3, 0.45, 1.0),
                  fg=(0.50, 0.62, 1.10), expo=1.25, spark=1.0, pop=1.3),
    "pleiades": dict(name="PLEIADES", l2="~1,000 STARS · 444 LY AWAY", sir=st["pleiades"]["n_sirius"],
                     near=f"{st['pleiades']['nearest_ly']:.1f} LY", tc=(130, 190, 255),
                     hyg=1.0, mw=0.85, cl="pleiades", core=M45, beams=[(0.35, 0.65, 1.0), (0.55, 0.45, 1.0), (0.3, 0.95, 1.0), (0.8, 0.85, 1.0)],
                     bI=0.45, air=0.10, aircol=(0.35, 0.55, 1.0), fg=(0.45, 0.66, 1.30), expo=1.15, neb=1.0, spark=1.3, pop=3.2, ng=70, gth=3.5),
    "hyades": dict(name="HYADES", l2="~700 STARS · 153 LY AWAY", sir=st["hyades"]["n_sirius"],
                   near=f"{st['hyades']['nearest_ly']:.1f} LY", tc=(255, 170, 90),
                   hyg=1.0, mw=0.95, cl="hyades", core=HYA, beams=[(1.0, 0.55, 0.15), (1.0, 0.8, 0.4), (0.4, 0.8, 1.0), (1.0, 0.35, 0.2)],
                   bI=0.7, air=0.04, aircol=(0.6, 0.5, 0.8), fg=(1.0, 0.72, 0.55), expo=1.2, spark=1.2, pop=4.0, ng=40, gth=3.0),
    "omega": dict(name="OMEGA CENTAURI", l2="~10 MILLION STARS · 17,000 LY AWAY", sir=st["omega"]["n_sirius"],
                  near=f"{st['omega']['nearest_ly']:.2f} LY", tc=(255, 200, 90),
                  hyg=0.0, mw=0.0, cl="omega", core="az180alt50", beams=[(1.0, 0.75, 0.25), (1.0, 0.5, 0.15), (1.0, 0.9, 0.6), (1.0, 0.45, 0.55)],
                  bI=1.0, air=0.75, aircol=(0.40, 0.42, 1.0), fg=(1.0, 0.80, 0.50), expo=0.85, spark=1.0, hp=0.7),
    "nsc": dict(name="GALACTIC CENTRE", l2="~1.5 MILLION STARS WITHIN 3 LY", sir=st["nsc"]["n_sirius"],
                near=f"{st['nsc']['nearest_ly'] * 365.25:.0f} LIGHT-DAYS", tc=(255, 215, 140),
                hyg=0.0, mw=0.0, cl="nsc", core="az180alt62", beams=[(1.0, 0.85, 0.5), (0.5, 0.75, 1.0), (1.0, 0.45, 0.75), (1.0, 0.65, 0.2)],
                bI=1.25, air=0.45, aircol=(0.55, 0.45, 0.85), fg=(1.0, 0.84, 0.62), expo=0.55, spark=0.9, hp=0.30, fk=0.55, gpop=2.2, vlim=-0.8, fblur=3.5, ng=70, gth=12.0, dust=1.0, glowcol=(1.0, 0.60, 0.30)),
}


def round_count(n):
    if n < 100: return fmt(n)
    if n < 1000: return "~" + fmt(int(round(n, -1)))
    return "~" + fmt(int(round(n, -2)))


# ------------------------------------------------------------------------------------------------- helpers
_T = np.linspace(1500, 45000, 1024)
BB = np.stack([bbcolor(x) for x in _T]).astype(f32)
def star_rgb(T):
    c = BB[np.clip(((T - 1500) / (45000 - 1500) * 1023).astype(np.int32), 0, 1023)]
    y = c @ np.array([0.2126, 0.7152, 0.0722], f32)
    c = y[:, None] + (c - y[:, None]) * 1.7                                 # vivid star colours (as star-dates)
    c = np.clip(c, 0.02, None); c /= (c @ np.array([0.2126, 0.7152, 0.0722], f32))[:, None]
    return c.astype(f32)


def palette(x):
    x = x[..., None] if np.ndim(x) else x
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (x - np.array([0.0, 0.33, 0.67], f32)))
    return (c ** 2.2).astype(f32)


def pal_list(cols, x):
    C = np.array(list(cols) + [cols[0]], f32); n = len(cols)
    p = (x % 1.0) * n; i = np.floor(p).astype(np.int32); fr = (p - i)[..., None]
    return C[i] * (1 - fr) + C[i + 1] * fr


def rot_to(target):
    """3x3 R with R @ (0,0,1) = target (unit)"""
    z = target / np.linalg.norm(target)
    a = np.array([0.0, 0.0, 1.0]) if abs(z[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    x = np.cross(a, z); x /= np.linalg.norm(x); y = np.cross(z, x)
    return np.stack([x, y, z], 1)


def disp_flux(V):
    """display flux of a point star (perceptual compression of the huge range)"""
    return (4.0 * 10 ** (-0.4 * 0.80 * V)).astype(f32)


# ------------------------------------------------------------------------------------------------- scene
class Scene:
    def __init__(self, vertical=True):
        assert vertical, "this Short is 9:16 only"
        self.L = L = Layout(True); W, H = L.W, L.H
        self.fg = fg = Foreground(FG_PATH, L, hz_frac=0.80)
        self.hz = fg.horizon
        self.lens = lens_for(True, self.hz)
        L.cap_y = 1000
        self.caps = Captions(L, WORDS, emphasis={"THOUSAND", "CLUSTER", "PLEIADES", "DOZENS", "SIRIUS", "HYADES", "GIANTS",
                                                 "OMEGA", "CENTAURI", "10 MILLION", "MILLION", "THOUSANDS", "DARK", "HEART",
                                                 "MOON", "SUBURBS", "BLUE", "NEVER"})
        self.hs = 2                                                            # half-res grid for smooth layers
        self.rays = self.lens.rays(1)
        self.rays_h = self.lens.rays(self.hs)
        alt = np.arcsin(np.clip(self.rays[..., 2], -1, 1)).astype(f32)
        e = np.clip(alt / (np.pi / 2), 0, 1)
        self.e = e
        k = np.exp(-e / 0.28)[..., None]
        zen = np.array([0.014, 0.010, 0.075], f32); hor = np.array([0.034, 0.046, 0.200], f32)
        night = zen * (1 - k) + hor * k
        night += np.exp(-((e - 0.40) / 0.22) ** 2)[..., None] * np.array([0.018, 0.003, 0.034], f32)
        n = cv2.resize(fbm2((96, 96), 61, 3.0), (W, H), interpolation=cv2.INTER_CUBIC)
        self.night = (night * (1 + 0.06 * n)[..., None]).astype(f32)
        # scattered starlight (the atmosphere lit by the cluster): brighter low down, Rayleigh-ish
        self.airgrad = (0.35 + 0.65 * np.exp(-e / 0.35)).astype(f32)
        self.above = smooth(-0.01, 0.05, alt).astype(f32)
        self.a = fg.a[..., None]
        yy, xx = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xx, yy
        hy, hx = np.mgrid[0:H // 2, 0:W // 2].astype(f32) * 2 + 1.0; self.hx, self.hy = hx, hy
        # foreground bases
        f = fg.flat; y = lum(f)[..., None]
        self.fg_night = ((f * 0.40 + y * 0.60) * np.array([0.21, 0.21, 0.52], f32) * 1.15).astype(f32)
        self.fg_lit = (f * 0.75 + y * 0.25).astype(f32)                        # colour-preserving lit base
        self.trees = (fg.a * (1 - fg.ground) * ((xx < 330) | (xx > 790)) * (yy > 820)).astype(f32)
        self.mw = canvas(os.path.join(SCR, "mw_gal.npz"))
        # ---- real sky (HYG): field stars
        z = np.load(os.path.join(SCR, "stars.npz"))
        ra, de, V, ci, ly = z["ra"], z["dec"], z["mag"], z["ci"], z["ly"]
        keep = V < 6.5
        sv = eq_vec(ra, de)
        def near(c, deg): return sv @ eq_vec(*c) > math.cos(math.radians(deg))
        self.hyg_members = {"pleiades": near(M45, 1.3) & (ly > 300) & (ly < 600), "hyades": near(HYA, 10) & (ly > 120) & (ly < 190)}
        self.hyg = dict(d=sv[keep].astype(np.float64), V=V[keep], col=star_rgb(np.clip(bv_temp(np.clip(ci[keep], -0.4, 2.0)), 2600, 30000)),
                        mem={k: v[keep] for k, v in self.hyg_members.items()})
        self.sets = {}
        self.back = None
        self.ph_rng = np.random.default_rng(3)
        self.neb_tex = self.nebula_tex()
        self.r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 7 + self.r.uniform(-0.25, 0.25), w=self.r.uniform(0.10, 0.20), I=self.r.uniform(0.8, 1.2),
                           hue=self.r.uniform(0, 1), ph=self.r.uniform(0, 6.28), sp=self.r.uniform(0.6, 1.4)) for i in range(7)]

    # ----------------------------------------------------------------------------------------------- data per scene
    def core_eq(self, key):
        c = SCN[key]["core"]
        if c is None: return None
        if isinstance(c, tuple): return eq_vec(*c)
        az, alt = (180.0, 50.0) if c == "az180alt50" else (180.0, 62.0)
        ts = T_SW[{"omega": "ome", "nsc": "nsc"}[key]]
        lst_mid = LST(ts + 4.0)
        return eq2hor(lst_mid).T @ hdir(az, alt)

    def get(self, key):
        """point stars (eq-frame unit vectors, V, colour, display flux), faint map + its rotation, light stats"""
        if key in self.sets: return self.sets[key]
        S = SCN[key]; d_, V_, c_ = [], [], []
        if S["hyg"] > 0:
            m = np.ones(len(self.hyg["V"]), bool)
            if S["cl"] in self.hyg["mem"]: m &= ~self.hyg["mem"][S["cl"]]           # we are inside: drop its members as seen from Earth
            d_.append(self.hyg["d"][m]); V_.append(self.hyg["V"][m]); c_.append(self.hyg["col"][m])
        R = None; faint = None
        if S["cl"]:
            z = np.load(os.path.join(SCR, f"cl_{S['cl']}.npz"))
            R = rot_to(self.core_eq(key))
            vlim = S.get("vlim", 6.5)
            sel = z["V"] < vlim
            d_.append(z["dirs"][sel].astype(np.float64) @ R.T); V_.append(z["V"][sel]); c_.append(star_rgb(z["T"][sel]))
            fm = z["faint"].astype(f32)
            # add the 6.5..7 stars back into the faint map (they were kept as points by clusters.py)
            rest = ~sel
            if rest.any():
                u = z["dirs"][rest]; f = 10 ** (-0.4 * z["V"][rest])
                MH, MW_ = fm.shape
                ra = np.degrees(np.arctan2(u[:, 1], u[:, 0])) % 360.0; dec = np.degrees(np.arcsin(np.clip(u[:, 2], -1, 1)))
                xi = np.clip((ra / 360 * MW_).astype(int), 0, MW_ - 1); yi = np.clip(((90 - dec) / 180 * MH).astype(int), 0, MH - 1)
                dec_c = 90 - (yi + 0.5) / MH * 180
                pix_sr = (2 * np.pi / MW_) * (np.pi / MH) * np.cos(np.radians(dec_c))
                np.add.at(fm, (yi, xi), (f / pix_sr).astype(f32))
            faint = cv2.GaussianBlur(fm, (0, 0), S.get("fblur", 1.2))
        d = np.concatenate(d_); V = np.concatenate(V_).astype(f32); col = np.concatenate(c_)
        o = np.argsort(V); d, V, col = d[o], V[o], col[o]
        out = dict(d=d, V=V, col=col, fd=disp_flux(V), ph=self.ph_rng.uniform(0, 1000, len(V)).astype(f32), R=R, faint=faint)
        out["light"] = self.light_stats(out, key)
        self.sets[key] = out
        return out

    def light_stats(self, s, key):
        """illuminance on the ground (relative units, physical flux 10^-0.4V * sin(alt)) and its colour; the 3 brightest
        sources for shadows"""
        ts = {"today": 0.0, "pleiades": T_SW["ple"], "hyades": T_SW["hya"], "omega": T_SW["ome"], "nsc": T_SW["nsc"]}[key]
        lst = LST(ts + 2.0)
        h = s["d"] @ eq2hor(lst).T
        sa = np.clip(h[:, 2], 0, 1)
        f = 10 ** (-0.4 * s["V"].astype(np.float64)) * sa
        E = float(f.sum()); col = (f[:, None] * s["col"]).sum(0) / max(E, 1e-30)
        if s["faint"] is not None:
            fm = s["faint"]; MH, MW_ = fm.shape
            dec_c = np.radians(90 - (np.arange(MH) + 0.5) / MH * 180); ra_c = np.radians((np.arange(MW_) + 0.5) / MW_ * 360)
            v = np.stack([np.cos(dec_c)[:, None] * np.cos(ra_c)[None], np.cos(dec_c)[:, None] * np.sin(ra_c)[None],
                          np.sin(dec_c)[:, None] * np.ones_like(ra_c)[None]], -1) @ s["R"].T @ eq2hor(lst).T
            pix_sr = (2 * np.pi / MW_) * (np.pi / MH) * np.cos(dec_c)[:, None]
            E += float((fm * pix_sr * np.clip(v[..., 2], 0, 1)).sum())
        if SCN[key]["hyg"] > 0: E *= 1.0
        top = np.argsort(-f)[:3]
        x, y, ok = self.lens.project(h[top])
        return dict(E=E, col=col.astype(f32), top=[(float(x[i]), float(y[i]), float(np.degrees(np.arcsin(sa[top[i]]))), float(f[top[i]] / max(E, 1e-30)))
                                                  for i in range(len(top))])

    # ----------------------------------------------------------------------------------------------- layers
    def nebula_tex(self):
        """striated blue reflection-nebula texture (Merope-nebula look), half res, periodic"""
        n1 = fbm2((512, 512), 71, 2.4); n2 = fbm2((512, 512), 72, 1.6)
        ridge = (1 - np.abs(n2)) ** 4
        k = np.zeros((31, 31), f32); k[15, :] = 1
        k = cv2.warpAffine(k, cv2.getRotationMatrix2D((15, 15), 35, 1.0), (31, 31)); k /= k.sum()
        streak = cv2.filter2D(ridge, -1, k, borderType=cv2.BORDER_WRAP)
        n3 = fbm2((512, 512), 73, 3.0)
        tex = np.clip(np.clip(n3 * 0.45 + 0.55, 0, 2) ** 1.6 * (0.75 + 0.5 * streak) + 0.25 * np.clip(n1 * 0.5 + 0.5, 0, 2), 0, 3)
        return tex.astype(f32)

    def dust(self, cx, cy, t):
        """dark, warped dust lanes cutting across the galactic-centre glow (half res transmission)"""
        if not hasattr(self, "_dn"):
            self._dn = (fbm2((512, 512), 91, 2.8), fbm2((512, 512), 92, 2.2))
        n1, n2 = self._dn
        a = math.radians(-22)
        x = self.hx - cx; y = self.hy - cy
        u = x * math.cos(a) + y * math.sin(a); v = -x * math.sin(a) + y * math.cos(a)
        mu = ((u * 0.45 + t * 3.0) % 512).astype(f32); mv = ((v * 0.45) % 512).astype(f32)
        w1 = cv2.remap(n1, mu, mv, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        w2 = cv2.remap(n2, mu, ((v * 0.9) % 512).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        vv = v + 70 * w1
        lanes = (np.exp(-((vv - 40) / 55) ** 2) * 1.0 + np.exp(-((vv + 170) / 35) ** 2) * 0.8
                 + np.exp(-((vv - 290) / 40) ** 2) * 0.7) * np.clip(0.55 + 0.45 * w2, 0, 1)
        lanes += np.clip(w2 - 0.9, 0, 1) * 0.5 * np.exp(-np.abs(v) / 500)
        return np.clip(1 - 0.93 * lanes, 0.05, 1).astype(f32)

    def mw_layer(self, lst):
        M = EQ2GAL @ eq2hor(lst).T
        g = self.rays_h @ M.T.astype(f32)
        l = np.arctan2(g[..., 1], g[..., 0]); b = np.arcsin(np.clip(g[..., 2], -1, 1))
        mx = (WL / 2 + np.degrees(l) * PXD) % WL; my = HB / 2 - np.degrees(b) * PXD
        return cv2.remap(self.mw, mx.astype(f32), my.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)

    def faint_layer(self, s, lst):
        """integrated light of the unresolved cluster stars (flux / sr) -> half-res map"""
        M = s["R"].T @ eq2hor(lst).T
        g = self.rays_h @ M.T.astype(f32)
        MH, MW_ = s["faint"].shape
        ra = np.degrees(np.arctan2(g[..., 1], g[..., 0])) % 360.0; dec = np.degrees(np.arcsin(np.clip(g[..., 2], -1, 1)))
        mx = ra / 360 * MW_ - 0.5; my = (90 - dec) / 180 * MH - 0.5
        return cv2.remap(s["faint"], mx.astype(f32), my.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)

    def stars_layer(self, s, t, lst, gain=1.0, spark=1.0, hp=0.85, pop=1.0, ng=28, gth=6.0, gpop=None):
        gpop = pop if gpop is None else gpop
        """all point stars: bilinear splat (bincount), scintillation, multi-scale halos for the bright ones, 4-point glints"""
        L = self.L; W, H = L.W, L.H
        h = s["d"] @ eq2hor(lst).T
        vis = np.where(h[:, 2] > -0.01)[0]
        h = h[vis]
        x, y, ok = self.lens.project(h)
        sel = ok & (x > -2) & (x < W + 1) & (y > -2) & (y < H + 1)
        idx = vis[sel]; x = x[sel]; y = y[sel]; zz = h[sel, 2]
        ph = s["ph"][idx]
        nt = np.sin(t * 13.1 + ph) * 0.5 + np.sin(t * 23.7 + ph * 1.7) * 0.3 + np.sin(t * 37.3 + ph * 2.3) * 0.2
        sig = np.clip(0.10 + 0.35 * np.exp(-zz / 0.15), 0.08, 0.6) * spark
        tw = np.exp(sig * nt * 1.6 - 0.5 * sig * sig)
        ext = np.clip(zz / 0.12, 0, 1) ** 0.7
        fd = s["fd"][idx] * tw * ext * gain
        core = np.minimum(fd, 5.0)
        col = s["col"][idx]
        acc = np.zeros(((H + 2) * (W + 2), 3), f32)
        x0 = np.floor(x).astype(np.int64); y0 = np.floor(y).astype(np.int64); fx = (x - x0); fy = (y - y0)
        for dy, dx, wg in ((0, 0, (1 - fx) * (1 - fy)), (0, 1, fx * (1 - fy)), (1, 0, (1 - fx) * fy), (1, 1, fx * fy)):
            li = (np.clip(y0 + dy, 0, H + 1) * (W + 2) + np.clip(x0 + dx, 0, W + 1))
            w_ = core * wg
            for c in range(3):
                acc[:, c] += np.bincount(li, weights=w_ * col[:, c], minlength=(H + 2) * (W + 2)).astype(f32)
        acc = acc.reshape(H + 2, W + 2, 3)[:H, :W]
        st = cv2.GaussianBlur(acc, (0, 0), 0.7) * 2.4
        # halos: the excess over the core cap, at quarter res, three scales
        big = fd > 2.0
        if big.any():
            q = 4; hq, wq = H // q, W // q
            hb = np.zeros((hq * wq, 3), f32)
            xi = np.clip((x[big] / q).astype(np.int64), 0, wq - 1); yi = np.clip((y[big] / q).astype(np.int64), 0, hq - 1)
            ex = (fd[big] - 2.0 * 0.6) ** hp * pop
            for c in range(3):
                hb[:, c] = np.bincount(yi * wq + xi, weights=ex * col[big, c], minlength=hq * wq)
            hb = hb.reshape(hq, wq, 3)
            halo = cv2.GaussianBlur(hb, (0, 0), 0.8) * 0.30 + cv2.GaussianBlur(hb, (0, 0), 2.5) * 0.050 + cv2.GaussianBlur(hb, (0, 0), 8.0) * 0.008
            st += cv2.resize(halo, (W, H), interpolation=cv2.INTER_LINEAR)
        # glints on the brightest
        order = list(np.argsort(-fd)[:ng])
        red = np.where(col[:, 0] > 1.6 * col[:, 2])[0]
        order += [j for j in red[np.argsort(-fd[red])][:max(ng // 3, 8)] if j not in order]
        for j in order:
            g = fd[j]
            if g < gth * (0.5 if col[j, 0] > 1.6 * col[j, 2] else 1.0): continue
            c = col[j] * 0.85 + 0.15
            Lk = min((6 + 7 * math.log(g / 6 + 1) ** 1.2) * gpop ** 0.5, 46.0)
            a = min(g, 150.0) ** 0.8 * 0.06 * gpop * (1 + 0.25 * math.sin(t * 5 + ph[j]))
            splat(st, x[j], y[j], int(Lk * 4) + 6, lambda d, dx, dy: ((np.exp(-np.abs(dy) / 0.8) * np.exp(-np.abs(dx) / Lk) + np.exp(-np.abs(dx) / 0.8) * np.exp(-np.abs(dy) / Lk)) * a)[..., None] * c)
        return st, (x, y, fd, col)

    def beams_layer(self, t, S, cx, cy, I):
        """coloured light beams radiating from the cluster core direction (half res)"""
        if I <= 0.003 or not S["beams"]: return None
        dx = self.hx - cx; dy = self.hy - cy
        d = np.sqrt(dx * dx + dy * dy) + 1e-3; phi = np.arctan2(dy, dx) + 0.25 * np.log(d / 30.0)
        rad = (1 - np.exp(-(d + 6) / 45)) * (np.exp(-d / 1400) * 0.9 + 0.1)
        acc = np.zeros(dx.shape + (3,), f32)
        for b in self.beams:
            a = b["a"] + 0.05 * t * b["sp"]
            dp = (phi - a + np.pi) % (2 * np.pi) - np.pi
            wd = b["w"] * (1 + 0.25 * math.sin(t * 0.9 * b["sp"] + b["ph"]))
            g = np.exp(-(dp / wd) ** 2 * 1.6)
            Ib = b["I"] * (0.72 + 0.28 * math.sin(t * 1.3 * b["sp"] + b["ph"] * 2))
            xh = (b["hue"] + dp / wd * 0.25) % 1.0
            acc += pal_list(S["beams"], xh) * (g * Ib)[..., None]
        return acc * rad[..., None] * 0.30 * I

    def nebula(self, t, cx, cy, pts):
        """blue reflection-nebula glow around the brightest Pleiades stars (screen space, rides with the core)"""
        x, y, fd, col = pts
        acc = np.zeros(self.hx.shape, f32)
        for j in np.argsort(-fd)[:14]:
            if fd[j] < 8: break
            R = 110 + 40 * math.log(fd[j])
            acc += np.exp(-np.sqrt((self.hx - x[j]) ** 2 + (self.hy - y[j]) ** 2) / R) * math.log(fd[j] / 4)
        u = ((self.hx - cx) * 0.5 + t * 2.0) % 512; v = ((self.hy - cy) * 0.5) % 512
        tex = cv2.remap(self.neb_tex, u.astype(f32), v.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        wide = np.exp(-np.sqrt((self.hx - cx) ** 2 + (self.hy - cy) ** 2) / 520) * 0.35
        return ((acc * 0.55 + wide) * tex ** 1.4)[..., None] * np.array([0.12, 0.34, 1.0], f32) * 0.20

    # ----------------------------------------------------------------------------------------------- sky of one scene
    def sky(self, key, t, lst, fade_in=1.0):
        """HDR sky (no foreground) of scene `key`; returns (img, info)"""
        S = SCN[key]; s = self.get(key); W, H = self.L.W, self.L.H
        sky = self.night.copy()
        lt = s["light"]
        if S["air"] > 0:
            ac = np.array(S["aircol"], f32) * (0.5 + 0.5 * lt["col"] / max(lt["col"].max(), 1e-6))
            sky += (self.airgrad * S["air"] * 0.05)[..., None] * ac
        half = np.zeros((H // 2, W // 2, 3), f32)
        if S["mw"] > 0: half += self.mw_layer(lst) * 6.0 * S["mw"]
        if s["faint"] is not None:
            fl = self.faint_layer(s, lst)
            # unresolved starlight: flux/sr -> display (compressed); colour from the mean light
            fc = 0.35 + 0.65 * lt["col"] / max(lt["col"].max(), 1e-6)
            if S.get("glowcol"): fc = np.array(S["glowcol"], f32)
            half += ((np.maximum(fl, 0) / 100.0) ** 0.6 * 0.05 * S.get("fk", 1.0))[..., None] * fc[None, None, :]
        core = None
        ce = self.core_eq(key)
        if ce is not None:
            hc = eq2hor(lst) @ ce
            cx, cy, okc = self.lens.project(hc[None]); core = (float(cx[0]), float(cy[0]))
        sky += cv2.resize(half, (W, H), interpolation=cv2.INTER_LINEAR)
        stl, pts = self.stars_layer(s, t, lst, gain=fade_in, spark=S["spark"], hp=S.get("hp", 0.85), pop=S.get("pop", 1.0),
                                    ng=S.get("ng", 28), gth=S.get("gth", 6.0), gpop=S.get("gpop"))
        if S.get("dust") and core is not None:
            tr = self.dust(core[0], core[1], t)
            sky = self.night + (sky - self.night) * cv2.resize(tr, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
            stl = stl * cv2.resize(np.maximum(tr, 0.35), (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
        sky += stl
        if S.get("neb") and core is not None:
            sky += cv2.resize(self.nebula(t, core[0], core[1], pts), (W, H), interpolation=cv2.INTER_LINEAR) * fade_in
        return sky * self.above[..., None] + self.night * (1 - self.above[..., None]), dict(core=core, pts=pts)

    # ----------------------------------------------------------------------------------------------- foreground
    def relight(self, key, t):
        S = SCN[key]; lt = self.get(key)["light"]; E0 = self.get("today")["light"]["E"]
        g = (lt["E"] / E0) ** 0.30
        tint = np.array(S["fg"], f32) * (0.6 + 0.4 * lt["col"] / max(lt["col"].max(), 1e-6))
        lit = smooth(1.2, 5.0, g)
        out = (self.fg_night * (1 - lit) + self.fg_lit * tint * 0.07 * lit) * g
        # faint multiple star shadows from the brightest sources
        if g > 1.4:
            sh = np.zeros(self.fg.a.shape, f32)
            for (sx, sy, alt, share) in lt["top"]:
                if share < 0.004 or alt < 5: continue
                sh += self.shadow(sx, alt) * min(share * 6, 0.55)
            out = out * (1 - np.clip(sh, 0, 0.7))[..., None]
        return out

    _shc = {}
    def shadow(self, sx, alt):
        k = (int(sx / 8), int(alt))
        if k in self._shc: return self._shc[k]
        W, H = self.L.W, self.L.H
        yb = 1505.0                                                              # tree bases (plate rows)
        ky = 0.32 / max(math.tan(math.radians(alt)), 0.25)                       # shadow length on the foreshortened ground
        kx = -np.clip((sx - W / 2) / 900.0, -1.2, 1.2) * 0.9
        yo = self.yy; xo = self.xx
        hgt = np.maximum(yo - yb, 0) / ky                                        # tree height that lands here
        srcy = (yb - hgt).astype(f32); srcx = (xo - hgt * kx * ky * 1.6).astype(f32)
        m = cv2.remap(self.trees, srcx, srcy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        m = cv2.GaussianBlur(m * (yo > yb) * self.fg.ground, (0, 0), 5.0)
        self._shc[k] = m.astype(f32)
        return self._shc[k]

    # ----------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        L = self.L; W, H = L.W, L.H; fg = self.fg
        lst = LST(t)
        cur, prev, t0, t1 = scene_at(t)
        S = SCN[cur]
        u = t - t0
        in_swap = 0 <= u < REVEAL and t0 > 0
        # ---- sky: new scene inside the expanding shockwave, old one outside
        sky_new, info = self.sky(cur, t, lst, fade_in=(0.4 + 0.6 * ramp(u, 0, 0.5)) if t0 > 0 and cur != "today" else 1.0)
        c_sw = info["core"] if (info["core"] is not None and cur != "today") else (W / 2, 700.0)
        if in_swap and cur != "today":
            sky_old, _ = self.sky(prev, t, lst)
            R = 2600 * (u / REVEAL) ** 0.65
            d = np.sqrt((self.xx - c_sw[0]) ** 2 + (self.yy - c_sw[1]) ** 2)
            m = smooth(R + 40, R - 40, d)[..., None]
            sky = sky_new * m + sky_old * (1 - m)
        else:
            sky = sky_new
        # anticipation glow at the coming core before each swap
        nxt = [(ts, k) for ts, k in SWAPS if ts > t]
        if nxt and nxt[0][1] != "today" and nxt[0][0] - t < 0.6:
            ts, k = nxt[0]; v = 1 - (ts - t) / 0.6
            ce = self.core_eq(k); hc = eq2hor(lst) @ ce; px, py, _ = self.lens.project(hc[None])
            dd = np.sqrt((self.hx - px[0]) ** 2 + (self.hy - py[0]) ** 2)
            gcol = np.array(SCN[k]["beams"][0], f32)
            sky += cv2.resize((np.exp(-dd / (40 + 160 * v)) * 1.6 * v ** 2)[..., None] * gcol, (W, H), interpolation=cv2.INTER_LINEAR)
        # beams from the core: burst at the swap, then a slow persistent glow
        if cur != "today" and info["core"] is not None:
            I = S["bI"] * (0.35 + 1.4 * math.exp(-max(u, 0) / 0.9)) * ramp(u, 0.0, 0.25)
            if t1 < 1e8: I *= 1 - 0.6 * ramp(t, t1 - 0.5, t1)
            bm = self.beams_layer(t, S, info["core"][0], info["core"][1], I)
            if bm is not None: sky += cv2.resize(bm, (W, H), interpolation=cv2.INTER_LINEAR) * self.above[..., None]
        # target ring on the real Pleiades in today's sky (the hook), from "star cluster"
        if cur == "today" and t < T_SW["ple"]:
            self.target_ring(sky, t, lst)
        # ---- foreground
        if in_swap and prev != cur:
            w = ramp(u, 0.0, 0.7)
            fgc = self.relight(prev, t) * (1 - w) + self.relight(cur, t) * w
        else:
            fgc = self.relight(cur, t)
        if cur == "today" and t > T_BACK:
            pass
        img = sky * (1 - self.a) + fgc * self.a
        # ---- swap flash + chromatic shockwave
        for ts, k in SWAPS:
            uu = t - ts
            if -0.05 < uu < 1.4:
                fc = 0.45 + 0.55 * np.array(SCN[k]["beams"][0] if SCN[k]["beams"] else (0.8, 0.9, 1.0), f32)
                if k == "today": continue
                ce = self.core_eq(k); hc = eq2hor(lst) @ ce; px, py, _ = self.lens.project(hc[None]); px, py = float(px[0]), float(py[0])
                img += (2.2 * math.exp(-max(uu, 0) / 0.07) * ease((uu + 0.05) / 0.05)) * fc
                R = 2600 * (max(uu, 0) / REVEAL) ** 0.65; wdt = 16 + 50 * uu
                hd = np.sqrt((self.hx - px) ** 2 + (self.hy - py) ** 2)
                ring = np.zeros(hd.shape + (3,), f32)
                for ch, off in ((0, 12), (1, 0), (2, -12)):
                    ring[..., ch] = np.exp(-((hd - R - off) / wdt) ** 2) * 2.0 * math.exp(-max(uu, 0) / 0.55)
                img += cv2.resize(ring, (W, H), interpolation=cv2.INTER_LINEAR)
        # ---- final white-out -> today's quiet sky
        if T_WO0 < t < T_BACK:
            v = ease((t - T_WO0) / (T_BACK - T_WO0))
            img = img + (30 * v ** 2.5) * np.array([1.0, 0.95, 0.88], f32)
        if T_BACK <= t < T_BACK + 0.6:
            img = img + (30 * (1 - ease((t - T_BACK) / 0.6)) ** 2.2) * np.array([1.0, 0.95, 0.88], f32)
        img = self.chroma_bloom(img, 1.0)
        expo = S["expo"]
        if in_swap and prev != cur: expo = SCN[prev]["expo"] * (1 - ramp(u, 0, 0.6)) + S["expo"] * ramp(u, 0, 0.6)
        out = tonemap(img, expo)
        out = self.grade(out)
        out = finish(out, t, grain=0.010, vignette=0.16)
        self.overlay(out, t, cur, t0)
        return out

    def target_ring(self, sky, t, lst):
        """pulsing chromatic target ring on the real Pleiades (M45) while the hook says 'star cluster'"""
        a = ramp(t, wt("hook", "NOW") - 0.1, wt("hook", "NOW") + 0.4)
        if a <= 0: return
        hc = eq2hor(lst) @ eq_vec(*M45); px, py, _ = self.lens.project(hc[None]); px, py = float(px[0]), float(py[0])
        lay = np.zeros_like(sky)
        for k in range(3):
            ph = ((t * 0.9 + k / 3) % 1.0)
            R = 40 + 160 * ph; al = a * (1 - ph) ** 1.5 * 3.0
            for ch, off in ((0, 5), (1, 0), (2, -5)):
                c = [0.0, 0.0, 0.0]; c[ch] = float(al * (0.7, 0.9, 1.2)[ch])
                cv2.circle(lay, (int(px * 4), int(py * 4)), int((R + off) * 4), tuple(c), 3, cv2.LINE_AA, 2)
        cv2.circle(lay, (int(px * 4), int(py * 4)), int(34 * 4), (0.8 * a, 1.2 * a, 2.0 * a), 3, cv2.LINE_AA, 2)
        sky += lay + cv2.GaussianBlur(lay, (0, 0), 4.0) * 1.5

    def chroma_bloom(self, img, amt):
        img = bloom(img, 0.85 * amt)
        H, W = img.shape[:2]
        sm = cv2.resize(img, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
        sm = np.maximum(sm - 1.0, 0)
        acc = np.empty_like(sm)
        for c, s in ((0, 26), (1, 20), (2, 15)):
            acc[..., c] = cv2.GaussianBlur(sm[..., c], (0, 0), s)
        return img + cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR) * 0.35 * amt

    def grade(self, out):
        y = out.mean(2, keepdims=True)
        out = y + (out - y) * 1.18
        return np.clip(out + np.array([0.010, 0.008, 0.024], f32) * (1 - out), 0, 1)

    # ----------------------------------------------------------------------------------------------- overlay
    def overlay(self, out, t, cur, t0):
        L = self.L; W = L.W
        S = SCN[cur]
        x, ys = W / 2, (1185, 1268, 1322, 1372)
        a = ramp(t, max(t0, 0.0) + 0.25, max(t0, 0.0) + 0.55)
        nxt = [ts for ts, k in SWAPS if ts > t]
        if nxt: a *= 1 - ramp(t, nxt[0] - 0.35, nxt[0] - 0.12)
        if cur == "today" and t > T_BACK: a = ramp(t, T_BACK + 0.7, T_BACK + 1.0) * (1 - ramp(t, DUR - 0.12, DUR))
        if cur == "today" and t < 1.0: a = ramp(t, 0.12, 0.45)
        if T_WO0 < t < T_BACK + 0.6: a = 0.0
        if a > 0.01:
            if self.back is None:
                self.back = (1 - 0.42 * np.exp(-((self.yy - 1290) / 120) ** 4) * np.exp(-((self.xx - W / 2) / 470) ** 6))[..., None].astype(f32)
            out *= 1 - (1 - self.back) * a
            dy = (1 - a) * 18
            big = int(L.hud_size * (1.45 if len(S["name"]) < 12 else 1.2))
            rgba, _ = word_layer(S["name"], big, W * 0.9, fill=S["tc"])
            composite(out, rgba, x, ys[0] + dy, a)
            hud_text(out, S["l2"], x, ys[1] + dy, int(L.hud_size * 0.56), "Black", (255, 255, 255), a, 0.06, display=True)
            # counter ticks up after the swap
            n = S["sir"]; cnt = int(round(n * ease((t - t0 - 0.15) / 0.6))) if (t0 > 0 and cur != "today") else n
            ctxt = fmt(cnt) if cnt < 1000 or cnt != n else round_count(n)
            hud_text(out, f"STARS BRIGHTER THAN SIRIUS: {ctxt}", x, ys[2] + dy, int(L.hud_size * 0.48), "Bold", (255, 236, 170), a, 0.08, display=True)
            hud_text(out, f"NEAREST STAR: {S['near']}", x, ys[3] + dy, int(L.hud_size * 0.48), "Bold", (200, 230, 255), a, 0.08, display=True)
        self.caps.draw(out, t)


# ------------------------------------------------------------------------------------------------- run
def save(im, p):
    Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p)


def run(stills=None):
    sc = Scene(True); tag = "vert"
    if stills:
        os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
        for t in stills:
            t0 = time.time(); save(sc.frame(t), os.path.join(SCR, "stills", f"{tag}_{t:05.2f}.png"))
            print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)
        return
    n = int(round(DUR * FPS))
    enc = Encoder(os.path.join(SCR, f"video_{tag}.mp4"), sc.L.W, sc.L.H, FPS, crf=17)
    t0 = time.time()
    for i in range(n):
        enc.write(sc.frame(i / FPS))
        if i % 60 == 0: print(f"{tag} frame {i}/{n}  {time.time() - t0:.0f}s", flush=True)
    enc.close(); print("done", time.time() - t0, "DUR", DUR)


def patch(ranges):
    """re-render only frames inside `ranges` [(t0, t1)], copying the others from the existing render"""
    import subprocess
    sc = Scene(True); tag = "vert"
    W, H = sc.L.W, sc.L.H; src = os.path.join(SCR, f"video_{tag}.mp4"); old = src.replace(".mp4", "_prev.mp4")
    os.replace(src, old)
    dec = subprocess.Popen(["nice", "-n", "10", "ffmpeg", "-v", "error", "-i", old, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = Encoder(src, W, H, FPS, crf=17)
    for i in range(int(round(DUR * FPS))):
        buf = dec.stdout.read(W * H * 3); t = i / FPS
        if any(a <= t <= b for a, b in ranges) or len(buf) < W * H * 3: enc.write(sc.frame(t))
        else: enc.p.stdin.write(buf)
    enc.close(); dec.wait(); os.remove(old); print("patched")


if __name__ == "__main__":
    if sys.argv[1] == "info":
        print("DUR", DUR); [print(l["key"], l["start"], l["end"]) for l in PL]
        print({k: round(v, 2) for k, v in T_SW.items()}, "back", round(T_BACK, 2)); sys.exit()
    if sys.argv[1] == "patch":
        patch([tuple(float(v) for v in r.split(":")) for r in sys.argv[2].split(",")]); sys.exit()
    st_ = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    run(st_)
