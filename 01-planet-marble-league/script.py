"""
PLANET MARBLE LEAGUE  -  "Marble race through every planet 🪐 Pick yours!"
=========================================================================
One self-contained, fully procedural Blender script (Blender 4.2 - 5.x).

  Scripting tab:  open this file, press ▶ (builds the scene, bakes the race)
  Headless:       blender -b -P script.py -- --render            (final render)
                  blender -b -P script.py -- --preview           (fast preview)
                  blender -b -P script.py -- --seed 42 --render  (another race)
  Physics only:   python3 script.py -- --sim-only   (no Blender needed: runs the
                  race + verification and prints the result)

HOW THE PER-ZONE GRAVITY WORKS (read README.md for the full story)
  Blender has ONE global scene gravity, and its force fields can't be cleanly
  box-bounded (spherical / tube falloff only) and couple to Bullet rigid bodies
  with a strength that is not a clean acceleration.  So the race is simulated by
  a small deterministic physics engine in this file: rolling spheres in a
  half-pipe track, sphere-sphere collisions, 1200 Hz fixed sub-steps, and the
  gravity vector picked per marble per sub-step from the zone the marble is in.
  The result is baked to keyframes (every frame) -> deterministic playback, and
  everything on screen (positions, tower, podium, standings) is read from it.
"""

import sys
import os
import math
import random
import time
from array import array

try:
    import bpy
    HAVE_BPY = True
except ImportError:          # allows `python3 script.py -- --sim-only`
    bpy = None
    HAVE_BPY = False

# =============================================================================
# CONFIG
# =============================================================================
CONFIG = {
    "seed": 3,                    # race seed: start grid order + tiny nudges
    # Zone order along the track (name must exist in PLANETS below).  The track
    # features (chicane, floaty bumps, hairpin, gap jump, sprint) belong to the
    # planet, so reordering moves the features with it (pacing will change).
    "zone_order": ["EARTH", "MOON", "JUPITER", "PLUTO", "SUN"],
    "fps": 30,
    "duration_s": 75.0,
    "resolution": (1080, 1920),   # vertical short
    "engine": "EEVEE",            # 'EEVEE' (auto-picks 4.x/5.x id), 'CYCLES', 'WORKBENCH'
    "mode": "PREVIEW",            # 'PREVIEW' or 'RENDER' (CLI flags override)
    "preview_scale": 50,          # % resolution in PREVIEW
    "eevee_samples": {"PREVIEW": 8, "RENDER": 64},
    "cycles_samples": {"PREVIEW": 16, "RENDER": 128},
    "output_dir": "//render_marble_league/",   # '//' = next to the .blend / cwd
    "render_on_run": False,       # True -> render the animation after building
    "use_emoji": True,            # Blender 5.x text has emoji fallback; set False
                                  # if your build shows boxes instead of emoji
    # --- physics ---------------------------------------------------------
    "marble_radius": 0.30,        # m. 3 cm marbles scaled x10 (g kept real)
    "substeps_hz": 1200,          # fixed integrator rate (Sun g=274 needs it)
    "rolling_resistance": 0.01,   # c_rr     } rolling loss while touching the track:
    "rolling_drag": 0.004,        # c_v [s²/m²] }  decel = (c_rr + c_v v²) * normal load
    "restitution_track": 0.35,
    "restitution_marble": 0.6,
    "gate_open_s": 2.0,           # video time when the start gate drops
    "max_sim_s": 95.0,
}

PLANETS = {
    #           g [m/s²]  floor strip       sky colour            ground colour
    "EARTH":   (9.81,  (0.10, 0.55, 0.20), (0.30, 0.55, 0.95), (0.16, 0.38, 0.12)),
    "MOON":    (1.62,  (0.55, 0.55, 0.58), (0.004, 0.004, 0.008), (0.30, 0.30, 0.31)),
    "MARS":    (3.71,  (0.72, 0.30, 0.12), (0.80, 0.55, 0.35), (0.45, 0.18, 0.08)),
    "JUPITER": (24.79, (0.85, 0.45, 0.12), (0.75, 0.52, 0.30), (0.55, 0.38, 0.22)),
    "PLUTO":   (0.62,  (0.78, 0.86, 0.95), (0.006, 0.008, 0.02), (0.80, 0.82, 0.86)),
    "SUN":     (274.0, (1.00, 0.55, 0.05), (0.50, 0.16, 0.03), (1.00, 0.35, 0.03)),
}

# 8 marbles: (name, colour, finish)  finish: GLASS / METAL / PAINT
MARBLES = [
    ("1", (0.90, 0.10, 0.10), "GLASS"),
    ("2", (0.10, 0.35, 0.95), "METAL"),
    ("3", (0.98, 0.80, 0.05), "PAINT"),
    ("4", (0.10, 0.80, 0.30), "GLASS"),
    ("5", (0.65, 0.20, 0.90), "PAINT"),
    ("6", (1.00, 0.45, 0.05), "METAL"),
    ("7", (0.05, 0.85, 0.90), "GLASS"),
    ("8", (0.95, 0.35, 0.70), "PAINT"),
]

# Track, per planet: list of segments.
#   L      length [m]            turn  heading change [deg] (+ = left)
#   grade  dz/ds (neg = down)    bank  banking [deg] (sign follows the turn)
#   a      half width of the flat floor [m] (a0->a1 for a taper)
#   lip    how far the curved side walls go up [deg]; 90 = vertical lip
#   hump   height [m] of a smooth bump over the segment (floaty Moon jumps)
#   gap    True -> no floor and no walls (jump)
#   tag    feature name used for captions / camera cutaways
TRACK = {
    "EARTH": [
        dict(L=3.0, grade=-0.10, a=1.5, lip=88, tag="start"),
        dict(L=5.0, grade=-0.10, a0=1.5, a1=0.95, lip=88),
        dict(L=5.0, grade=-0.065),
        dict(L=3.6, turn=30, grade=-0.065, bank=8, tag="chicane"),
        dict(L=3.6, turn=-60, grade=-0.065, bank=10),
        dict(L=3.6, turn=60, grade=-0.065, bank=10),
        dict(L=3.6, turn=-30, grade=-0.065, bank=8),
        dict(L=3.0, grade=-0.065),
        dict(L=0.55, grade=-0.55, gap=True, tag="step"),      # small step-down
        dict(L=6.0, grade=-0.065),
    ],
    "MOON": [
        dict(L=4.0, grade=-0.065),
        dict(L=3.0, grade=-0.065, hump=0.22, lip=95, tag="bumps"),
        dict(L=3.0, grade=-0.065, hump=0.22, lip=95),
        dict(L=3.0, grade=-0.065, hump=0.22, lip=95),
        dict(L=4.0, grade=-0.065),
        dict(L=14.0, turn=-125, grade=-0.065, lip=115, bank=20, rw=0.75, tag="wideturn"),
        dict(L=5.0, grade=-0.065),
        dict(L=3.0, grade=-0.065, hump=0.2, lip=110),
        dict(L=6.0, turn=30, grade=-0.065, bank=8),
    ],
    "JUPITER": [
        dict(L=4.0, grade=-0.10),
        dict(L=8.0, grade=-0.15, tag="drop"),
        dict(L=2.0, grade=-0.12),
        dict(L=6.9, turn=180, grade=-0.05, lip=38, bank=10, a=0.6, rw=0.7, tag="hairpin"),
        dict(L=3.0, grade=-0.07),
        dict(L=10.0, turn=-60, grade=-0.075),
        dict(L=8.0, grade=-0.075),
    ],
    "PLUTO": [
        dict(L=3.0, grade=-0.075),
        dict(L=1.0, grade=0.0),
        dict(L=4.5, grade=-0.222, gap=True, tag="gap"),       # 1.0 m drop
        dict(L=6.0, grade=-0.02, a=1.25, lip=115, rw=0.75),
        dict(L=6.0, grade=-0.075, a0=1.25, a1=0.95, lip=115, rw=0.75),
        dict(L=14.0, turn=20, grade=-0.075, lip=115, bank=10, rw=0.75),
        dict(L=14.0, turn=-20, grade=-0.075, lip=115, bank=10, rw=0.75),
        dict(L=12.0, grade=-0.075, lip=115, rw=0.75),
    ],
    "SUN": [
        dict(L=3.0, grade=-0.12, tag="sprint"),
        dict(L=0.12, grade=-0.25, gap=True, tag="sunstep"),   # 3 cm step: airborne ~15 ms
        dict(L=10.0, grade=-0.12),
        dict(L=13.0, grade=-0.18),
        dict(L=14.0, grade=-0.25),
        dict(L=0.01, grade=-0.25, tag="finish"),
        dict(L=14.0, grade=-0.15, tag="runout"),
        dict(L=4.0, grade=0.0),
        dict(L=2.0, grade=0.20),
    ],
}

ZONE_LIP = {"MOON": 105, "PLUTO": 105}   # default wall lip per zone [deg]

DS = 0.04          # track sample spacing [m]
SMOOTH_N = 25      # moving-average window for curvature/grade/bank/width (1 m)


# =============================================================================
# CLI
# =============================================================================
def parse_args():
    argv = sys.argv
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    opts = {"sim_only": False}
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--render":
            CONFIG["mode"] = "RENDER"; CONFIG["render_on_run"] = True
        elif a == "--preview":
            CONFIG["mode"] = "PREVIEW"; CONFIG["render_on_run"] = True
        elif a == "--build-only":
            CONFIG["render_on_run"] = False
        elif a == "--seed" and i + 1 < len(args):
            CONFIG["seed"] = int(args[i + 1]); i += 1
        elif a == "--engine" and i + 1 < len(args):
            CONFIG["engine"] = args[i + 1].upper(); i += 1
        elif a == "--output" and i + 1 < len(args):
            CONFIG["output_dir"] = args[i + 1]; i += 1
        elif a == "--frames" and i + 1 < len(args):     # e.g. 100,900,1500
            opts["frames"] = [int(x) for x in args[i + 1].split(",")]; i += 1
        elif a == "--scale" and i + 1 < len(args):
            opts["scale"] = int(args[i + 1]); i += 1
        elif a == "--sim-only":
            opts["sim_only"] = True
        elif a == "--ff-test":
            opts["ff_test"] = True
        i += 1
    return opts


# =============================================================================
# small vector helpers (pure python, deterministic)
# =============================================================================
def v_add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def v_sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def v_mul(a, k): return (a[0] * k, a[1] * k, a[2] * k)
def v_dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def v_cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def v_len(a): return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])
def v_norm(a):
    n = v_len(a)
    return (a[0] / n, a[1] / n, a[2] / n) if n > 1e-12 else (0.0, 0.0, 0.0)
def lerp(a, b, t): return a + (b - a) * t
def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def q_mul(a, b):
    aw, ax, ay, az = a; bw, bx, by, bz = b
    return (aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw)


def q_axis_angle(axis, ang):
    s = math.sin(ang / 2)
    return (math.cos(ang / 2), axis[0] * s, axis[1] * s, axis[2] * s)


# =============================================================================
# TRACK  (centre line + half-pipe cross-section, sampled every DS metres)
# =============================================================================
class Track:
    def __init__(self, zone_order):
        self.zone_order = zone_order
        segs = []
        for zi, zname in enumerate(zone_order):
            for sd in TRACK[zname]:
                d = dict(sd); d["zone"] = zi; segs.append(d)
        self.segs = segs
        # ---- raw per-sample parameters
        zname_of = list(zone_order)
        k_raw, gr_raw, bank_raw, a_raw, lip_raw, rw_raw = [], [], [], [], [], []
        floor, zone, hump, seg_id = [], [], [], []
        for si, sg in enumerate(segs):
            n = max(1, int(round(sg["L"] / DS)))
            turn = math.radians(sg.get("turn", 0.0))
            bank = math.radians(sg.get("bank", 6.0 if sg.get("turn") else 0.0))
            bank = bank * (1 if turn > 0 else -1 if turn < 0 else 0)
            a0 = sg.get("a0", sg.get("a", 0.95)); a1 = sg.get("a1", sg.get("a", a0))
            for k in range(n):
                u = (k + 0.5) / n
                k_raw.append(turn / sg["L"])
                gr_raw.append(sg.get("grade", 0.0))
                bank_raw.append(bank)
                a_raw.append(lerp(a0, a1, u))
                lip_raw.append(math.radians(sg.get("lip", ZONE_LIP.get(zname_of[sg["zone"]], 80))))
                rw_raw.append(sg.get("rw", 0.55))
                floor.append(not sg.get("gap", False))
                zone.append(sg["zone"])
                hump.append(sg.get("hump", 0.0) * math.sin(math.pi * u) ** 2)
                seg_id.append(si)
        N = len(k_raw)

        def smooth(arr, w=SMOOTH_N, protect=None):
            out = []
            h = w // 2
            for i in range(len(arr)):
                lo, hi = max(0, i - h), min(len(arr), i + h + 1)
                out.append(sum(arr[lo:hi]) / (hi - lo))
            return out
        k_s = smooth(k_raw)
        bank_s = smooth(bank_raw, 2 * SMOOTH_N)
        a_s = smooth(a_raw)
        lip_s = smooth(lip_raw, 9)
        rw_s = smooth(rw_raw)
        # grade: smooth, but keep gaps sharp (take-off lip stays flat)
        gr_s = []
        h = SMOOTH_N // 4
        for i in range(N):
            lo, hi = max(0, i - h), min(N, i + h + 1)
            same = [gr_raw[j] for j in range(lo, hi) if floor[j] == floor[i]]
            gr_s.append(sum(same) / len(same))
        # ---- integrate the centre line
        P = []
        x = y = 0.0; z = 0.0; psi = math.radians(90.0)   # start heading +Y
        zc = []
        for i in range(N):
            psi += k_s[i] * DS
            x += math.cos(psi) * DS; y += math.sin(psi) * DS
            z += gr_s[i] * DS
            zc.append(z)
            P.append((x, y, z + hump[i]))
        # lift so the lowest point is at z = 0 + margin
        zmin = min(p[2] for p in P)
        P = [(p[0], p[1], p[2] - zmin + 3.0) for p in P]
        # arc length
        S = [0.0]
        for i in range(1, N):
            S.append(S[-1] + v_len(v_sub(P[i], P[i - 1])))
        # frames
        T, LAT, UP = [], [], []
        for i in range(N):
            t = v_norm(v_sub(P[min(N - 1, i + 1)], P[max(0, i - 1)]))
            lat0 = v_norm(v_cross((0, 0, 1), t))
            up0 = v_cross(t, lat0)
            b = bank_s[i]
            up = v_norm(v_add(v_mul(up0, math.cos(b)), v_mul(lat0, math.sin(b))))
            lat = v_cross(up, t)
            T.append(t); LAT.append(lat); UP.append(up)
        self.N, self.P, self.S, self.T, self.LAT, self.UP = N, P, S, T, LAT, UP
        self.A, self.LIP, self.FLOOR, self.ZONE, self.SEG = a_s, lip_s, floor, zone, seg_id
        self.RWS = rw_s            # side-wall radius per sample
        self.length = S[-1]
        # zone & feature positions (arc length)
        self.zone_start = {}
        for i in range(N):
            self.zone_start.setdefault(zone[i], S[i])
        self.feature = {}
        for i in range(N):
            tag = segs[seg_id[i]].get("tag")
            if tag and tag not in self.feature:
                self.feature[tag] = (S[i], i)
        # end of feature segments too
        self.feature_end = {}
        for i in range(N):
            tag = segs[seg_id[i]].get("tag")
            if tag:
                self.feature_end[tag] = (S[i], i)
        self.s_finish = self.feature["finish"][0]
        self.ground_z = min(p[2] for p in P) - 2.5     # one flat ground under everything
        self.s_gate = 2.75

    def zone_of_s(self, s):
        zi = 0
        for k, s0 in self.zone_start.items():
            if s >= s0 and k > zi:
                zi = k
        return zi

    def index_of_s(self, s):
        # binary search
        lo, hi = 0, self.N - 1
        while lo < hi:
            m = (lo + hi) // 2
            if self.S[m] < s: lo = m + 1
            else: hi = m
        return lo

    def world(self, s, l, h):
        i = self.index_of_s(s)
        t = s - self.S[i]
        o = v_add(self.P[i], v_mul(self.T[i], t))
        return v_add(o, v_add(v_mul(self.LAT[i], l), v_mul(self.UP[i], h)))

    def floor_h(self, i, l):
        """Height of the floor/side surface at lateral l (for meshing)."""
        a = self.A[i]; R = self.RWS[i]
        if abs(l) <= a:
            return 0.0
        d = abs(l) - a
        return R - math.sqrt(max(0.0, R * R - d * d))

    def self_check(self):
        """Report places where non-adjacent track parts come too close."""
        P, S = self.P, self.S
        worst = (99, None)
        step = 10
        for i in range(0, self.N, step):
            for j in range(i + step, self.N, step):
                if S[j] - S[i] < 12.0:
                    continue
                dx = P[i][0] - P[j][0]; dy = P[i][1] - P[j][1]
                dh = math.hypot(dx, dy); dz = abs(P[i][2] - P[j][2])
                if dz < 2.2 and dh < worst[0]:
                    worst = (dh, (round(S[i], 1), round(S[j], 1)))
        return worst


# =============================================================================
# SIMULATION  (deterministic rolling-sphere engine with per-zone gravity)
# =============================================================================
RACING, FINISHED, OUT = 0, 1, 2
DEBUG = bool(os.environ.get("PML_DEBUG"))


class Marble:
    def __init__(self, idx, p, v):
        self.idx = idx
        self.p = p; self.v = v
        self.hint = 0
        self.status = RACING
        self.s = 0.0; self.l = 0.0; self.h = 0.0
        self.zone = 0
        self.contact_n = None
        self.load = 0.0            # normal load per unit mass (for rolling resistance)
        self.q = (1.0, 0.0, 0.0, 0.0)
        self.omega = (0.0, 0.0, 0.0)
        self.finish_t = None
        self.out_t = None; self.out_zone = None; self.out_reason = ""
        self.zone_entry = {}
        self.ground_z = None
        self.slow_time = 0.0
        self.dbg = []
        self.hit = False


def gravity_of_zone(track, zi):
    return PLANETS[track.zone_order[zi]][0]


def locate(track, m, p):
    """Nearest centre-line sample around the marble's hint -> (i, s, l, h)."""
    P = track.P
    best = None; bi = m.hint
    lo = max(0, m.hint - 5); hi = min(track.N - 1, m.hint + 8)
    for j in range(lo, hi + 1):
        q = P[j]
        d = (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2
        if best is None or d < best:
            best = d; bi = j
    m.hint = bi
    d = v_sub(p, P[bi])
    t = v_dot(d, track.T[bi])
    s = track.S[bi] + t
    l = v_dot(d, track.LAT[bi])
    h = v_dot(d, track.UP[bi])
    return bi, s, l, h


def track_contact(track, i, l, h, r):
    """Penetration depth and inward normal (nl, nh) in the (lat, up) plane."""
    if not track.FLOOR[i]:
        return 0.0, None
    a = track.A[i]; R = track.RWS[i]
    if h < -0.12:               # below the floor shell -> no contact
        return 0.0, None
    if abs(l) <= a:
        if h < r:
            return r - h, (0.0, 1.0)
        return 0.0, None
    sg = 1.0 if l > 0 else -1.0
    dl = l - sg * a; dh = h - R
    dist = math.hypot(dl, dh)
    if dist < 1e-9:
        return 0.0, None
    if dist <= R - r:
        return 0.0, None
    if dist > R + 0.10:          # outside the wall shell
        return 0.0, None
    cosang = -dh / dist         # 1 at the bottom, 0 at vertical
    if cosang < math.cos(track.LIP[i]):
        return 0.0, None        # above the lip: open air
    pen = dist - (R - r)
    return pen, (-dl / dist, -dh / dist)


def simulate(track, seed, verbose=True, start=None, tmax=None):
    cfg = CONFIG
    r = cfg["marble_radius"]
    dt = 1.0 / cfg["substeps_hz"]
    fps = cfg["fps"]
    sub_per_frame = int(round(cfg["substeps_hz"] / fps))
    crr = cfg["rolling_resistance"]; cv = cfg["rolling_drag"]
    e_tr = cfg["restitution_track"]; e_mm = cfg["restitution_marble"]
    rng = random.Random(seed)

    # ---- seeded start grid + nudges
    order = list(range(len(MARBLES)))
    rng.shuffle(order)
    slots = []
    for row, s0 in enumerate([2.35, 1.65]):
        for col, l0 in enumerate([1.05, 0.35, -0.35, -1.05]):
            slots.append((s0, l0))
    marbles = [None] * len(MARBLES)
    grid = {}
    for slot_i, mi in enumerate(order):
        s0, l0 = slots[slot_i]
        s0 += rng.uniform(-0.03, 0.03); l0 += rng.uniform(-0.04, 0.04)
        p = track.world(s0, l0, r)
        t0 = track.T[track.index_of_s(s0)]
        lat0 = track.LAT[track.index_of_s(s0)]
        v = v_add(v_mul(t0, rng.uniform(0.0, 0.08)), v_mul(lat0, rng.uniform(-0.06, 0.06)))
        m = Marble(mi, p, v)
        m.hint = track.index_of_s(s0)
        m.zone_entry[0] = 0.0
        # start pose: number decal (+X) turned towards the hook camera (front/above)
        spin = rng.uniform(-0.25, 0.25)
        face = v_norm(v_add(v_mul(t0, 0.55), (0.0, 0.0, 0.85)))
        axis = v_cross((1.0, 0.0, 0.0), face)
        ang = math.acos(max(-1.0, min(1.0, face[0])))
        q0 = q_axis_angle(v_norm(axis), ang) if v_len(axis) > 1e-9 else (1.0, 0.0, 0.0, 0.0)
        m.q = q_mul(q_axis_angle(face, spin), q0)
        marbles[mi] = m
        grid[mi] = slot_i
    if start is not None:          # test harness: [(s, l, speed), ...]
        marbles = []
        for k, (s0, l0, sp) in enumerate(start):
            i0 = track.index_of_s(s0)
            m = Marble(k, track.world(s0, l0, r), v_mul(track.T[i0], sp))
            m.hint = i0; m.zone = track.ZONE[i0]
            marbles.append(m)
    # ---- logs
    frames = []                         # per frame: list of (p, q, s, status, zone, speed)
    zlog = [array('d') for _ in marbles]        # z per sub-step
    alog = [array('b') for _ in marbles]        # 1 = airborne (no contact)
    zonelog = [array('b') for _ in marbles]
    events = []                          # (t, kind, marble, info)
    n_sub = 0
    t = 0.0
    tmax = tmax or cfg["max_sim_s"]

    def snapshot():
        frames.append([(m.p, m.q, m.s, m.status, m.zone, v_len(m.v)) for m in marbles])

    snapshot()
    while True:
        for m in marbles:
            g = gravity_of_zone(track, m.zone)
            ax, ay, az = 0.0, 0.0, -g
            n = m.contact_n
            if n is not None:
                an = az * n[2]
                # rolling without slipping: tangential response is 5/7
                ax = an * n[0] + 5.0 / 7.0 * (ax - an * n[0])
                ay = an * n[1] + 5.0 / 7.0 * (ay - an * n[1])
                az = an * n[2] + 5.0 / 7.0 * (az - an * n[2])
                vn = v_dot(m.v, n)
                vt = (m.v[0] - vn * n[0], m.v[1] - vn * n[1], m.v[2] - vn * n[2])
                sp = v_len(vt)
                if sp > 1e-6:
                    dec = (crr + cv * sp * sp) * min(m.load, 6.0 * g)
                    if dec * dt > sp:
                        dec = sp / dt
                    ax -= dec * vt[0] / sp; ay -= dec * vt[1] / sp; az -= dec * vt[2] / sp
            vx = m.v[0] + ax * dt; vy = m.v[1] + ay * dt; vz = m.v[2] + az * dt
            m.v = (vx, vy, vz)
            m.p = (m.p[0] + vx * dt, m.p[1] + vy * dt, m.p[2] + vz * dt)
            m.contact_n = None; m.load = 0.0
            if m.status == OUT:
                # free flight / rolling on the zone ground
                if m.p[2] < m.ground_z + r:
                    m.p = (m.p[0], m.p[1], m.ground_z + r)
                    vz = m.v[2]
                    if vz < 0:
                        vz = -e_tr * vz if vz < -0.6 else 0.0
                        m.v = (m.v[0], m.v[1], vz)
                    m.contact_n = (0.0, 0.0, 1.0); m.load = g
                    # extra scrub on the dirt so it stops
                    f = max(0.0, 1.0 - 0.6 * dt * 3)
                    m.v = (m.v[0] * f, m.v[1] * f, m.v[2])
                continue
            i, s, l, h = locate(track, m, m.p)
            if s > track.S[-1] - r:          # end wall
                tt = track.T[track.N - 1]
                m.p = v_sub(m.p, v_mul(tt, s - (track.S[-1] - r)))
                vn = v_dot(m.v, tt)
                if vn > 0:
                    m.v = v_sub(m.v, v_mul(tt, (1 + e_tr) * vn))
            pen, nn = track_contact(track, i, l, h, r)
            if pen > 0:
                nw = v_add(v_mul(track.LAT[i], nn[0]), v_mul(track.UP[i], nn[1]))
                m.p = v_add(m.p, v_mul(nw, pen))
                vn = v_dot(m.v, nw)
                if vn < 0:
                    if vn < -0.45:
                        m.v = v_sub(m.v, v_mul(nw, (1 + e_tr) * vn))
                    else:
                        m.v = v_sub(m.v, v_mul(nw, vn))
                        m.load = -vn / dt
                m.contact_n = nw
                if m.load == 0.0:
                    m.load = max(0.0, g * nw[2])
            m.s = s; m.l = l; m.h = h
            if DEBUG and n_sub % 60 == 0:
                m.dbg.append((round(t, 2), round(s, 1), round(l, 2), round(h, 2), round(v_len(m.v), 2)))
            zi = track.ZONE[i]
            if zi != m.zone:
                if zi > m.zone:
                    m.zone_entry[zi] = t
                m.zone = zi
            # finish line
            if m.status == RACING and s >= track.s_finish:
                m.status = FINISHED
                m.finish_t = t
                events.append((t, "finish", m.idx, None))
            # out of the track?
            if m.status == RACING:
                a = track.A[i]
                if abs(l) > a + track.RWS[i] + 0.35 or (h < -0.9):
                    m.status = OUT
                    m.out_t = t; m.out_zone = m.zone
                    m.out_reason = "jumped the wall" if abs(l) > a + 0.2 else "fell"
                    m.ground_z = track.ground_z
                    events.append((t, "out", m.idx, (track.zone_order[m.zone], m.out_reason, round(m.s, 1))))
                    if os.environ.get("PML_DEBUG"):
                        print("OUT", m.idx, "t=%.2f s=%.2f l=%.2f h=%.2f v=%s a=%.2f" % (t, s, l, h, tuple(round(c, 2) for c in m.v), a), "hist", [d for d in m.dbg if d[1] > 118][::4])
                elif m.s < track.s_finish:
                    # stuck detector (rolled back & stopped)
                    if v_len(m.v) < 0.05 and t > 2.0:
                        m.slow_time += dt
                        if m.slow_time > 6.0:
                            m.status = OUT; m.out_t = t; m.out_zone = m.zone
                            m.out_reason = "stalled"; m.ground_z = track.ground_z
                            events.append((t, "out", m.idx, track.zone_order[m.zone]))
                    else:
                        m.slow_time = 0.0
        # ---- marble - marble collisions
        nm = len(marbles); d2 = 4 * r * r
        for a_i in range(nm):
            A = marbles[a_i]
            for b_i in range(a_i + 1, nm):
                B = marbles[b_i]
                dx = A.p[0] - B.p[0]
                if dx > 2 * r or dx < -2 * r: continue
                dy = A.p[1] - B.p[1]
                if dy > 2 * r or dy < -2 * r: continue
                dz = A.p[2] - B.p[2]
                dd = dx * dx + dy * dy + dz * dz
                if dd >= d2 or dd < 1e-12: continue
                dist = math.sqrt(dd)
                A.hit = True; B.hit = True
                nx, ny, nz = dx / dist, dy / dist, dz / dist
                corr = (2 * r - dist) * 0.5
                A.p = (A.p[0] + nx * corr, A.p[1] + ny * corr, A.p[2] + nz * corr)
                B.p = (B.p[0] - nx * corr, B.p[1] - ny * corr, B.p[2] - nz * corr)
                vr = (A.v[0] - B.v[0]) * nx + (A.v[1] - B.v[1]) * ny + (A.v[2] - B.v[2]) * nz
                if vr < 0:
                    j = -(1 + e_mm) * vr * 0.5
                    A.v = (A.v[0] + j * nx, A.v[1] + j * ny, A.v[2] + j * nz)
                    B.v = (B.v[0] - j * nx, B.v[1] - j * ny, B.v[2] - j * nz)
        # ---- logs
        for k, m in enumerate(marbles):
            zlog[k].append(m.p[2]); alog[k].append(1 if (m.contact_n is None and not m.hit) else 0)
            m.hit = False
            zonelog[k].append(m.zone)
        n_sub += 1
        t = n_sub * dt
        if n_sub % sub_per_frame == 0:
            # visual spin: integrate rolling rotation over the frame
            for m in marbles:
                if m.contact_n is not None:
                    m.omega = v_mul(v_cross(m.contact_n, m.v), 1.0 / r)
                w = v_len(m.omega)
                if w > 1e-6:
                    dq = q_axis_angle(v_mul(m.omega, 1.0 / w), w / fps)
                    m.q = q_mul(dq, m.q)
                    qn = math.sqrt(sum(c * c for c in m.q)); m.q = tuple(c / qn for c in m.q)
            snapshot()
            done = all(m.status != RACING for m in marbles)
            if (done and t > track_done_pad(marbles, t)) or t >= tmax:
                break
    for m in marbles:
        if m.status == RACING:
            m.status = OUT; m.out_t = t; m.out_reason = "time limit"; m.out_zone = m.zone
    return dict(frames=frames, marbles=marbles, zlog=zlog, alog=alog, zonelog=zonelog,
                events=events, dt=dt, grid=grid, order=order)


def track_done_pad(marbles, t):
    last = max([m.finish_t or 0 for m in marbles] + [m.out_t or 0 for m in marbles])
    return last + 3.0


# =============================================================================
# VERIFICATION
# =============================================================================
def measure_airborne_g(sim, track):
    """Vertical acceleration from the baked sub-step motion while airborne."""
    dt = sim["dt"]
    res = {}       # zone -> list of measured g
    for k in range(len(sim["marbles"])):
        z = sim["zlog"][k]; air = sim["alog"][k]; zn = sim["zonelog"][k]
        n = len(z); i = 2
        while i < n - 2:
            if air[i] and air[i - 1] and air[i + 1] and zn[i - 1] == zn[i] == zn[i + 1]:
                # find a run of airborne samples in one zone
                j = i
                while j + 1 < n and air[j + 1] and zn[j + 1] == zn[i]:
                    j += 1
                if j - i >= 6:
                    a0, a1 = i + 1, j - 1
                    acc = [(z[q + 1] - 2 * z[q] + z[q - 1]) / (dt * dt) for q in range(a0, a1)]
                    if acc:
                        res.setdefault(zn[i], []).append((sum(acc) / len(acc), (j - i) * dt, k))
                i = j + 1
            else:
                i += 1
    return res


def frame_rate_airborne_g(sim, track):
    """Same measurement but from the per-frame baked positions (what renders)."""
    fps = CONFIG["fps"]; dtf = 1.0 / fps
    frames = sim["frames"]
    sub = int(round(CONFIG["substeps_hz"] / fps))
    out = {}
    for k in range(len(sim["marbles"])):
        air = sim["alog"][k]; zn = sim["zonelog"][k]
        for f in range(1, len(frames) - 1):
            lo = (f - 1) * sub; hi = (f + 1) * sub
            if hi >= len(air) or lo < 0:
                continue
            if all(air[q] for q in range(lo, hi)) and zn[lo] == zn[hi - 1]:
                z0 = frames[f - 1][k][0][2]; z1 = frames[f][k][0][2]; z2 = frames[f + 1][k][0][2]
                out.setdefault(zn[lo], []).append((z2 - 2 * z1 + z0) / (dtf * dtf))
    return out


def boundary_test(track):
    """2-zone prototype: a marble flying across a zone boundary (no contact)."""
    dt = 1.0 / CONFIG["substeps_hz"]
    zi_a = 1; zi_b = 2
    s_b = track.zone_start[zi_b]
    m = Marble(0, track.world(s_b - 1.2, 0.0, 6.0), (0, 0, 0))
    i0 = track.index_of_s(s_b - 1.2)
    m.v = v_mul(track.T[i0], 3.0)
    m.hint = i0
    zs, zonez = [], []
    for n in range(int(0.8 / dt)):
        i, s, l, h = locate(track, m, m.p)
        zi = track.ZONE[i]
        g = gravity_of_zone(track, zi)
        m.v = (m.v[0], m.v[1], m.v[2] - g * dt)
        m.p = v_add(m.p, v_mul(m.v, dt))
        zs.append(m.p[2]); zonez.append(zi)
    sub = int(round(CONFIG["substeps_hz"] / CONFIG["fps"]))
    rows = []
    fz = zs[::sub]; fzone = zonez[::sub]
    dtf = sub * dt
    for f in range(1, len(fz) - 1):
        a = (fz[f + 1] - 2 * fz[f] + fz[f - 1]) / (dtf * dtf)
        rows.append((f, track.zone_order[fzone[f]], -a))
    return rows


def freefall_test(g, h=1.0):
    dt = 1.0 / CONFIG["substeps_hz"]
    z = h; v = 0.0; t = 0.0
    while z > 0:
        v -= g * dt; zn = z + v * dt
        if zn <= 0:
            t += dt * z / (z - zn); break
        z = zn; t += dt
    return t


def verify(sim, track, verbose=True):
    zo = track.zone_order
    ms = sim["marbles"]
    lines = []
    P = lines.append
    P("=" * 72)
    P("PLANET MARBLE LEAGUE  - verification   seed=%d" % CONFIG["seed"])
    P("track length %.1f m, finish at s=%.1f m, %d samples" % (track.length, track.s_finish, track.N))
    P("zone starts: " + ", ".join("%s@%.1fm" % (zo[k], s) for k, s in sorted(track.zone_start.items())))
    gate = CONFIG["gate_open_s"]
    P("-- zone entry times (video seconds; gate drops at %.1f s)" % gate)
    P("   marble " + "".join("%9s" % z[:7] for z in zo) + "   FINISH")
    for m in ms:
        row = "   #%-5s " % MARBLES[m.idx][0]
        for zi in range(len(zo)):
            tt = m.zone_entry.get(zi)
            row += "%9s" % ("%.1f" % (tt + gate) if tt is not None else "-")
        row += "   " + ("%.2f" % (m.finish_t + gate) if m.finish_t is not None else
                        "DNF (%s in %s at %.1fs)" % (m.out_reason, zo[m.out_zone] if m.out_zone is not None else "?",
                                                    (m.out_t or 0) + gate))
        P(row)
    # measured gravity
    P("-- measured vertical acceleration while airborne (from the baked motion)")
    meas = measure_airborne_g(sim, track)
    fmeas = frame_rate_airborne_g(sim, track)
    ok_all = True
    for zi, zname in enumerate(zo):
        gt = PLANETS[zname][0]
        lst = meas.get(zi, [])
        fl = fmeas.get(zi, [])
        if lst:
            tot = sum(d for _, d, _ in lst)
            gm = -sum(a * d for a, d, _ in lst) / tot
            err = abs(gm - gt) / gt * 100
            fstr = ""
            if fl:
                gf = -sum(fl) / len(fl)
                fstr = " | per-frame keys: %.3f (%d frame triples)" % (gf, len(fl))
            P("   %-8s target %7.2f  measured %8.3f m/s²  (%.2f%%)  %d airborne runs, %.2f s total%s"
              % (zname, gt, gm, err, len(lst), tot, fstr))
            if err > 3.0:
                ok_all = False
        else:
            P("   %-8s target %7.2f  (no airborne phase in this zone)" % (zname, gt))
    assert ok_all, "zone gravity mismatch"
    P("   ASSERT OK: every zone's measured g is within 3% of the planet value")
    # 2-zone boundary prototype
    P("-- 2-zone boundary test (marble flying %s -> %s, per-frame second difference)" % (zo[1], zo[2]))
    rows = boundary_test(track)
    cross = next(n for n in range(1, len(rows)) if rows[n][1] != rows[n - 1][1])
    for f, zn, a in rows[max(0, cross - 3):cross + 4]:
        P("   frame %2d  zone %-8s  a_z = %7.3f m/s²" % (f, zn, a))
    gb = PLANETS[zo[2]][0]
    assert abs(rows[cross + 2][2] - gb) / gb < 0.01, "boundary test failed"
    P("   -> the acceleration switches inside one frame (the straddling frame mixes both)")
    # free fall
    P("-- free fall from 1 m (same integrator)  [brief: Pluto 1.8, Moon 1.1, Earth 0.45, Jupiter 0.28, Sun 0.09 s]")
    for zname in ["PLUTO", "MOON", "MARS", "EARTH", "JUPITER", "SUN"]:
        g = PLANETS[zname][0]
        tsim = freefall_test(g); tex = math.sqrt(2 / g)
        P("   %-8s g=%7.2f  t_sim=%.3f s  exact=%.3f s" % (zname, g, tsim, tex))
        assert abs(tsim - tex) / tex < 0.03
    P("-- corner speed ∝ √(μ g r):  Jupiter %.2f× Earth,  Moon %.2f× Earth,  Sun %.2f× Earth"
      % (math.sqrt(24.79 / 9.81), math.sqrt(1.62 / 9.81), math.sqrt(274 / 9.81)))
    # results
    fin = sorted([m for m in ms if m.finish_t is not None], key=lambda m: m.finish_t)
    dnf = [m for m in ms if m.finish_t is None]
    P("-- FINISHING ORDER")
    for k, m in enumerate(fin):
        gap = "" if k == 0 else "  +%.2f s" % (m.finish_t - fin[0].finish_t)
        P("   P%d  #%s  %.2f s%s" % (k + 1, MARBLES[m.idx][0], m.finish_t + gate, gap))
    for m in dnf:
        P("   DNF #%s  (%s, %s)" % (MARBLES[m.idx][0], m.out_reason, zo[m.out_zone] if m.out_zone is not None else "?"))
    lead = fin[0] if fin else None
    if lead:
        P("-- leader timing vs beat sheet (video s):  " + ", ".join(
            "%s %.1f" % (zo[zi], lead.zone_entry[zi] + gate) for zi in sorted(lead.zone_entry))
          + ", finish %.1f   [beats: Moon 15, Jupiter 30, Pluto 42, Sun 60, finish ~68]" % (lead.finish_t + gate))
    P("=" * 72)
    if verbose:
        print("\n".join(lines))
    return fin, dnf, lines


# =============================================================================
# main (physics part)
# =============================================================================
def run_physics(verbose=True):
    t0 = time.time()
    track = Track(CONFIG["zone_order"])
    sim = simulate(track, CONFIG["seed"])
    if verbose:
        print("simulated %.1f s of race in %.1f s wall time (%d sub-steps of 1/%d s)"
              % (len(sim["frames"]) / CONFIG["fps"], time.time() - t0,
                 len(sim["zlog"][0]), CONFIG["substeps_hz"]))
        print("track self-clearance (closest non-adjacent parts): %.2f m at s=%s" % track.self_check())
    fin, dnf, lines = verify(sim, track, verbose)
    sim["finish_order"] = fin; sim["dnf"] = dnf; sim["report"] = lines
    return track, sim



# =============================================================================
# DIRECTOR: the baked race -> a 75 s timeline (live race / slow-mo replay / podium)
# =============================================================================
class Director:
    def __init__(self, track, sim):
        self.track = track; self.sim = sim
        self.fps = CONFIG["fps"]
        self.nframes = int(round(CONFIG["duration_s"] * self.fps))
        self.gate = CONFIG["gate_open_s"]
        self.F = sim["frames"]
        self.ms = sim["marbles"]
        fin = sim["finish_order"]
        self.fin = fin
        g = self.gate
        # photo-finish group: everyone within 1.2 s of the winner (max 3)
        if fin:
            grp = [m for m in fin[:3] if m.finish_t - fin[0].finish_t < 1.2]
            self.group = grp
            self.live_end = min(max(grp[-1].finish_t + g + 0.4, 66.0), 71.0)
            self.replay_len = max(1.5, min(3.2, 75.0 - self.live_end - 2.6))
            self.replay_t0 = grp[0].finish_t - 0.55
            self.replay_t1 = grp[-1].finish_t + 0.3
        else:
            self.group = []
            self.live_end = 71.0; self.replay_len = 1.5
            self.replay_t0 = self.replay_t1 = 66.0
        self.replay_end = self.live_end + self.replay_len
        self.slowmo = (self.replay_t1 - self.replay_t0) / self.replay_len
        # leader progress per sim frame
        self.leader = []
        for row in self.F:
            self.leader.append(self.rank(row)[0])
        # first time any marble reaches a feature (sim s)
        self.feat_t = {}
        for tag, (s0, _) in track.feature.items():
            for fi, row in enumerate(self.F):
                if any(x[2] >= s0 and x[3] != OUT for x in row):
                    self.feat_t[tag] = fi / self.fps; break
        self.zone_t = {}
        for zi, s0 in track.zone_start.items():
            for fi, row in enumerate(self.F):
                if any(x[2] >= s0 and x[3] != OUT for x in row):
                    self.zone_t[zi] = fi / self.fps; break
        # hang time over the Pluto gap for the first marble across
        self.gap_hang = None
        if "gap" in track.feature:
            sg = track.feature["gap"][0]
            sub = int(round(CONFIG["substeps_hz"] / self.fps))
            best = None
            for k, m in enumerate(self.ms):
                for fi, row in enumerate(self.F):
                    if row[k][2] >= sg:
                        n0 = fi * sub; air = sim["alog"][k]
                        # walk back to take-off, then forward to landing
                        a = n0
                        while a > 0 and air[a - 1]: a -= 1
                        b = n0
                        while b < len(air) and (air[b] or (b - a) < 30):
                            b += 1
                        if best is None or fi < best[0]:
                            best = (fi, k, (b - a) * sim["dt"])
                        break
            if best:
                self.gap_hang = (best[1], best[2])

    # ---- ranking ----------------------------------------------------------
    def rank(self, row):
        def key(k):
            p, q, s, st, z, sp = row[k]
            m = self.ms[k]
            if st == FINISHED:
                return (0, m.finish_t)
            if st == OUT:
                return (2, -(m.out_t or 0))
            return (1, -s)
        return sorted(range(len(row)), key=key)

    # ---- sampling the baked sim at any sim time --------------------------
    def sample(self, ts):
        x = ts * self.fps
        n = len(self.F) - 1
        if x <= 0: return self.F[0]
        if x >= n: return self.F[n]
        i = int(x); u = x - i
        A = self.F[i]; B = self.F[i + 1]
        out = []
        for a, b in zip(A, B):
            p = tuple(lerp(a[0][j], b[0][j], u) for j in range(3))
            qa, qb = a[1], b[1]
            if sum(qa[j] * qb[j] for j in range(4)) < 0:
                qb = tuple(-c for c in qb)
            q = tuple(lerp(qa[j], qb[j], u) for j in range(4))
            qn = math.sqrt(sum(c * c for c in q)) or 1.0
            q = tuple(c / qn for c in q)
            out.append((p, q, lerp(a[2], b[2], u), a[3] if u < 0.5 else b[3], a[4], lerp(a[5], b[5], u)))
        return out

    def mode_at(self, tv):
        """-> (mode, sim_time)"""
        if tv < self.gate:
            return "hook", 0.0
        if tv < self.live_end:
            return "live", tv - self.gate
        if tv < self.replay_end:
            return "replay", self.replay_t0 + (tv - self.live_end) * self.slowmo
        return "podium", self.live_end - self.gate


# =============================================================================
# BLENDER SCENE
# =============================================================================
def bver():
    return bpy.app.version


def set_input(node, names, value):
    for n in names if isinstance(names, (list, tuple)) else [names]:
        if n in node.inputs:
            try:
                node.inputs[n].default_value = value
                return True
            except Exception:
                pass
    return False


def new_material(name):
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    return mat


def principled(name, color, metallic=0.0, rough=0.4, transmission=0.0, coat=0.0,
               emission=None, strength=0.0, alpha=1.0):
    mat = new_material(name)
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    set_input(bsdf, "Base Color", (*color, 1.0))
    set_input(bsdf, "Metallic", metallic)
    set_input(bsdf, "Roughness", rough)
    set_input(bsdf, ["Transmission Weight", "Transmission"], transmission)
    set_input(bsdf, ["Coat Weight", "Clearcoat"], coat)
    if emission is not None:
        set_input(bsdf, ["Emission Color", "Emission"], (*emission, 1.0))
        set_input(bsdf, "Emission Strength", strength)
    if alpha < 1.0:
        set_input(bsdf, "Alpha", alpha)
        blended(mat)
    mat.diffuse_color = (*color, 1.0)          # Workbench / viewport colour
    return mat


def blended(mat):
    if hasattr(mat, "surface_render_method"):
        try: mat.surface_render_method = "BLENDED"
        except Exception: pass
    if hasattr(mat, "blend_method"):
        try: mat.blend_method = "BLEND"
        except Exception: pass


def emission_mat(name, color, strength=1.0, alpha=1.0):
    mat = new_material(name)
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1.0)
    em.inputs["Strength"].default_value = strength
    if alpha < 1.0:
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        mix.inputs[0].default_value = alpha
        nt.links.new(tr.outputs[0], mix.inputs[1])
        nt.links.new(em.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
        blended(mat)
    else:
        nt.links.new(em.outputs[0], out.inputs["Surface"])
    mat.diffuse_color = (*color, alpha)
    return mat


def link(obj, coll=None):
    (coll or bpy.context.scene.collection).objects.link(obj)
    return obj


def mesh_obj(name, verts, faces, mats=None, mat_idx=None, smooth=False, coll=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    if mats:
        for m in mats:
            me.materials.append(m)
    if mat_idx is not None:
        me.polygons.foreach_set("material_index", mat_idx)
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    ob = bpy.data.objects.new(name, me)
    return link(ob, coll)


def box_obj(name, center, size, mat, rot=None, coll=None):
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    v = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
         (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    ob = mesh_obj(name, v, f, [mat], coll=coll)
    ob.location = center
    if rot is not None:
        ob.rotation_mode = "QUATERNION"; ob.rotation_quaternion = rot
    return ob


def text_obj(name, body, size, mat, align="CENTER", coll=None, bold=0.0):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = align
    cu.align_y = "CENTER"
    if bold:
        cu.offset = bold * size
    ob = bpy.data.objects.new(name, cu)
    ob.data.materials.append(mat)
    return link(ob, coll)


def no_shadow(ob):
    for attr in ("visible_shadow", "visible_diffuse", "visible_glossy", "visible_transmission",
                 "visible_volume_scatter"):
        if hasattr(ob, attr):
            try: setattr(ob, attr, False)
            except Exception: pass


def key_visible(ob, intervals, nframes):
    """Show `ob` only during the given (f0, f1) frame intervals (inclusive)."""
    state = [False] * (nframes + 2)
    for f0, f1 in intervals:
        for f in range(max(1, f0), min(nframes, f1) + 1):
            state[f] = True
    prev = None
    for f in range(1, nframes + 1):
        if state[f] != prev:
            ob.hide_render = not state[f]; ob.hide_viewport = not state[f]
            ob.keyframe_insert("hide_render", frame=f)
            ob.keyframe_insert("hide_viewport", frame=f)
            prev = state[f]


def emoji(txt, fallback):
    return txt if CONFIG["use_emoji"] else fallback


def reset_scene():
    if bpy.app.background:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        return bpy.context.scene
    sc = bpy.context.scene
    for ob in list(sc.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in list(sc.collection.children):
        bpy.data.collections.remove(coll)
    return sc


def setup_render(sc, nframes):
    r = sc.render
    sc.render.fps = CONFIG["fps"]
    sc.frame_start = 1; sc.frame_end = nframes
    r.resolution_x, r.resolution_y = CONFIG["resolution"]
    r.resolution_percentage = 100 if CONFIG["mode"] == "RENDER" else CONFIG["preview_scale"]
    eng = CONFIG["engine"].upper()
    if eng.startswith("EEVEE"):
        ids = ["BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"] if bver() < (5, 0, 0) else ["BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"]
        for e in ids:
            try:
                r.engine = e; break
            except Exception:
                continue
        try:
            sc.eevee.taa_render_samples = CONFIG["eevee_samples"][CONFIG["mode"]]
        except Exception:
            pass
    elif eng == "CYCLES":
        r.engine = "CYCLES"
        sc.cycles.samples = CONFIG["cycles_samples"][CONFIG["mode"]]
        try: sc.cycles.use_denoising = True
        except Exception: pass
    else:
        r.engine = "BLENDER_WORKBENCH"
        sc.display.shading.light = "STUDIO"
        sc.display.shading.color_type = "MATERIAL"
    # 'Standard' keeps the HUD white/yellow exact and the planet colours punchy
    try:
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.look = "None"
    except Exception:
        pass
    out = CONFIG["output_dir"]
    r.filepath = os.path.join(out, "planet_marble_league_")
    # video output (5.x has media_type), fall back to PNG frames
    try:
        ims = r.image_settings
        if hasattr(ims, "media_type"):
            ims.media_type = "VIDEO"
        ims.file_format = "FFMPEG"
        r.ffmpeg.format = "MPEG4"
        r.ffmpeg.codec = "H264"
        r.ffmpeg.constant_rate_factor = "HIGH"
        r.ffmpeg.audio_codec = "NONE"
    except Exception as e:
        print("FFmpeg output not available (%s) -> PNG frames" % e)
        try:
            r.image_settings.file_format = "PNG"
        except Exception:
            pass


# ---- track mesh -------------------------------------------------------------
def profile_points(track, i, n_arc=7):
    a = track.A[i]; R = track.RWS[i]; lip = track.LIP[i]
    pts = []
    for k in range(n_arc, 0, -1):                      # left wall, lip -> bottom
        ph = lip * k / n_arc
        pts.append((-a - R * math.sin(ph), R - R * math.cos(ph), 1))
    for k in range(5):
        pts.append((-a + 2 * a * k / 4, 0.0, 0))
    for k in range(1, n_arc + 1):
        ph = lip * k / n_arc
        pts.append((a + R * math.sin(ph), R - R * math.cos(ph), 1))
    return pts


def build_track(track, mats_floor, mat_wall, coll):
    step = 3
    idx = list(range(0, track.N, step))
    if idx[-1] != track.N - 1: idx.append(track.N - 1)
    verts, faces, fmat = [], [], []
    ring_start = []
    nprof = None
    for i in idx:
        pts = profile_points(track, i)
        nprof = len(pts)
        ring_start.append(len(verts))
        O = track.P[i]; L = track.LAT[i]; U = track.UP[i]
        for (l, h, _) in pts:
            verts.append(v_add(O, v_add(v_mul(L, l), v_mul(U, h))))
    kinds = [p[2] for p in profile_points(track, 0)]
    for r in range(len(idx) - 1):
        i0, i1 = idx[r], idx[r + 1]
        if not (track.FLOOR[i0] and track.FLOOR[i1]):
            continue
        if not all(track.FLOOR[j] for j in range(i0, i1 + 1)):
            continue
        z = track.ZONE[i0]
        for k in range(nprof - 1):
            a0 = ring_start[r] + k; b0 = ring_start[r + 1] + k
            faces.append((a0, b0, b0 + 1, a0 + 1))
            wall = kinds[k] == 1 or kinds[k + 1] == 1
            fmat.append(len(mats_floor) if wall else z)
    ob = mesh_obj("Track", verts, faces, list(mats_floor) + [mat_wall], fmat, smooth=True, coll=coll)
    mod = ob.modifiers.new("Thickness", "SOLIDIFY")
    mod.thickness = 0.05; mod.offset = -1.0
    return ob


def frame_quat(T, U):
    """Quaternion of a basis whose +Y is the track tangent and +Z is up."""
    from mathutils import Matrix, Vector
    y = Vector(T).normalized(); z = Vector(U)
    x = y.cross(z).normalized(); z = x.cross(y).normalized()
    return Matrix((x, y, z)).transposed().to_quaternion()


def build_scene(track, sim):
    from mathutils import Vector, Quaternion, Matrix
    t_build = time.time()
    D = Director(track, sim)
    nF = D.nframes; fps = D.fps
    sc = reset_scene()
    sc.name = "PlanetMarbleLeague"
    setup_render(sc, nF)
    zo = track.zone_order
    r = CONFIG["marble_radius"]

    def coll(name):
        c = bpy.data.collections.new(name); sc.collection.children.link(c); return c
    C_env, C_trk, C_mrb, C_hud = coll("Environment"), coll("Track"), coll("Marbles"), coll("HUD")

    def fr(tv):         # video time -> frame number
        return int(round(tv * fps)) + 1

    # ------------------------------------------------------------- materials
    zone_floor = []
    for z in zo:
        col = PLANETS[z][1]
        if z == "SUN":
            zone_floor.append(principled("floor_" + z, col, rough=0.5, emission=(1.0, 0.45, 0.05), strength=0.5))
        else:
            zone_floor.append(principled("floor_" + z, col, rough=0.45))
    m_wall = principled("track_wall", (0.85, 0.9, 0.95), rough=0.15, transmission=0.6, alpha=0.65)
    m_post = principled("post", (0.12, 0.12, 0.14), metallic=0.6, rough=0.4)
    m_white = emission_mat("hud_white", (1, 1, 1), 1.0)
    m_yellow = emission_mat("hud_yellow", (1.0, 0.82, 0.15), 1.0)
    m_red = emission_mat("hud_red", (1.0, 0.18, 0.15), 1.0)
    m_plate = emission_mat("hud_plate", (0.0, 0.0, 0.0), 1.0, alpha=0.72)
    m_red_plate = emission_mat("hud_redplate", (0.55, 0.02, 0.02), 1.0, alpha=0.85)
    m_sign = principled("sign", (0.03, 0.03, 0.05), rough=0.6)
    m_signtxt = emission_mat("sign_text", (1, 1, 1), 2.0)

    # ------------------------------------------------------------- world sky
    world = bpy.data.worlds.new("Sky"); sc.world = world
    if world.node_tree is None:
        world.use_nodes = True
    wn = world.node_tree.nodes; wl = world.node_tree.links
    bg = next(n for n in wn if n.type == "BACKGROUND")
    bg.inputs["Strength"].default_value = 1.0
    tc = wn.new("ShaderNodeTexCoord")
    vor = wn.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 180.0
    ramp = wn.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0; ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
    ramp.color_ramp.elements[1].position = 0.035; ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
    wl.new(tc.outputs["Generated"], vor.inputs["Vector"])
    wl.new(vor.outputs["Distance"], ramp.inputs["Fac"])
    starmix = wn.new("ShaderNodeMixRGB"); starmix.blend_type = "ADD"
    sky_rgb = wn.new("ShaderNodeRGB")
    wl.new(sky_rgb.outputs[0], starmix.inputs[1])
    wl.new(ramp.outputs["Color"], starmix.inputs[2])
    wl.new(starmix.outputs[0], bg.inputs["Color"])

    def sky_state(zname):
        return PLANETS[zname][2], (0.9 if zname in ("MOON", "PLUTO") else 0.0)

    # keyed by the zone the camera is looking at (leader's zone), 0.8 s blend
    sky_keys = []
    last = None
    for f in range(1, nF + 1):
        tv = (f - 1) / fps
        mode, ts = D.mode_at(tv)
        if mode in ("hook",):
            zname = zo[0]
        elif mode == "live":
            row = D.F[min(len(D.F) - 1, int(ts * fps))]
            zname = zo[row[D.leader[min(len(D.F) - 1, int(ts * fps))]][4]]
        else:
            zname = "SUN"
        if zname != last:
            sky_keys.append((f, zname)); last = zname
    for n, (f, zname) in enumerate(sky_keys):
        col, st = sky_state(zname)
        if n > 0:
            pcol, pst = sky_state(sky_keys[n - 1][1])
            sky_rgb.outputs[0].default_value = (*pcol, 1); starmix.inputs[0].default_value = pst
            sky_rgb.outputs[0].keyframe_insert("default_value", frame=f)
            starmix.inputs[0].keyframe_insert("default_value", frame=f)
        sky_rgb.outputs[0].default_value = (*col, 1); starmix.inputs[0].default_value = st
        f2 = f + (int(0.8 * fps) if n > 0 else 0)
        sky_rgb.outputs[0].keyframe_insert("default_value", frame=f2)
        starmix.inputs[0].keyframe_insert("default_value", frame=f2)

    # ------------------------------------------------------------- light
    ld = bpy.data.lights.new("KeyLight", "SUN"); ld.energy = 3.5; ld.angle = math.radians(3)
    lo = link(bpy.data.objects.new("KeyLight", ld), C_env)
    lo.rotation_euler = (math.radians(40), math.radians(10), math.radians(30))

    # ------------------------------------------------------------- ground (territory colours)
    import numpy as np
    P = np.array(track.P); Z = np.array(track.ZONE)
    sub = P[::10]; subz = Z[::10]
    xmin, ymin = P[:, 0].min() - 40, P[:, 1].min() - 40
    xmax, ymax = P[:, 0].max() + 40, P[:, 1].max() + 40
    step = 2.0
    nx = int((xmax - xmin) / step) + 1; ny = int((ymax - ymin) / step) + 1
    gx, gy = np.meshgrid(np.linspace(xmin, xmax, nx), np.linspace(ymin, ymax, ny))
    pts = np.stack([gx.ravel(), gy.ravel()], 1)
    d2 = ((pts[:, None, :] - sub[None, :, :2]) ** 2).sum(2)
    nearest = subz[d2.argmin(1)]
    gz = track.ground_z
    gverts = [(float(x), float(y), gz) for x, y in pts]
    gfaces = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            gfaces.append((a, a + 1, a + nx + 1, a + nx))
    gob = mesh_obj("Ground", gverts, gfaces, coll=C_env)
    me = gob.data
    ca = me.color_attributes.new("zone_col", "FLOAT_COLOR", "POINT")
    ga = me.color_attributes.new("glow", "FLOAT_COLOR", "POINT")
    cols = []; glows = []
    for zi in nearest:
        c = PLANETS[zo[int(zi)]][3]
        cols.extend((*c, 1.0)); g = 1.0 if zo[int(zi)] == "SUN" else 0.0
        glows.extend((g, g, g, 1.0))
    ca.data.foreach_set("color", cols); ga.data.foreach_set("color", glows)
    gm = new_material("ground")
    nt = gm.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "zone_col"
    at2 = nt.nodes.new("ShaderNodeAttribute"); at2.attribute_name = "glow"
    noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 0.6
    mixn = nt.nodes.new("ShaderNodeMixRGB"); mixn.blend_type = "MULTIPLY"; mixn.inputs[0].default_value = 0.35
    nt.links.new(at.outputs["Color"], mixn.inputs[1]); nt.links.new(noise.outputs["Color"], mixn.inputs[2])
    nt.links.new(mixn.outputs[0], bsdf.inputs["Base Color"])
    set_input(bsdf, "Roughness", 0.9)
    emi_in = "Emission Color" if "Emission Color" in bsdf.inputs else "Emission"
    nt.links.new(at.outputs["Color"], bsdf.inputs[emi_in])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = 0.7
    nt.links.new(at2.outputs["Fac"], mul.inputs[0])
    nt.links.new(mul.outputs[0], bsdf.inputs["Emission Strength"])
    gm.diffuse_color = (0.4, 0.4, 0.4, 1)
    me.materials.append(gm)

    # ------------------------------------------------------------- track, pillars, arches
    build_track(track, zone_floor, m_wall, C_trk)
    pill_me = bpy.data.meshes.new("pillar")
    pv, pf = [], []
    for k in range(8):
        a = 2 * math.pi * k / 8
        pv += [(0.09 * math.cos(a), 0.09 * math.sin(a), 0.0), (0.09 * math.cos(a), 0.09 * math.sin(a), 1.0)]
    for k in range(8):
        a, b = 2 * k, 2 * ((k + 1) % 8)
        pf.append((a, b, b + 1, a + 1))
    pill_me.from_pydata(pv, [], pf); pill_me.materials.append(m_post)
    s = 3.0
    while s < track.length:
        i = track.index_of_s(s)
        if track.FLOOR[i]:
            p = track.P[i]
            h = p[2] - 0.06 - gz
            if h > 0.3:
                ob = link(bpy.data.objects.new("pillar", pill_me), C_trk)
                ob.location = (p[0], p[1], gz); ob.scale = (1, 1, h)
        s += 6.0

    def arch(s0, label, colr, name):
        i = track.index_of_s(s0)
        O = Vector(track.P[i]); T = Vector(track.T[i]); Lh = Vector(track.LAT[i])
        Lh.z = 0; Lh.normalize()
        Th = Vector((T.x, T.y, 0)).normalized()
        half = track.A[i] + track.RWS[i] + 0.35
        hgt = 1.55
        q = frame_quat(Th, (0, 0, 1))
        m_arch = principled("arch_" + name, colr, rough=0.35, emission=colr, strength=0.4)
        for sgn in (-1, 1):
            c = O + Lh * (sgn * half) + Vector((0, 0, hgt / 2 - 0.1))
            box_obj("arch_post", c, (0.18, 0.18, hgt + 0.2), m_arch, q, C_trk)
        box_obj("arch_beam", O + Vector((0, 0, hgt)), (2 * half + 0.18, 0.2, 0.22), m_arch, q, C_trk)
        sign = box_obj("arch_sign", O + Vector((0, 0, hgt + 0.36)), (2 * half - 0.3, 0.08, 0.5), m_sign, q, C_trk)
        t = text_obj("arch_label", label, 0.3, m_signtxt, coll=C_trk, bold=0.03)
        # text faces the incoming marbles (normal = -T), up = +Z
        rot = Matrix((-Lh, Vector((0, 0, 1)), -Th)).transposed().to_quaternion()
        t.rotation_mode = "QUATERNION"; t.rotation_quaternion = rot
        t.location = O + Vector((0, 0, hgt + 0.36)) - Th * 0.05
        # fit the label into the sign
        bpy.context.view_layer.update()
        w = t.dimensions.x
        if w > 2 * half - 0.45:
            k = (2 * half - 0.45) / w
            t.scale = (k, k, k)

    for zi, z in enumerate(zo):
        arch(track.zone_start[zi] + (9.0 if zi == 0 else 0.0),
             "%s · %s m/s²" % (z, ("%g" % PLANETS[z][0])), PLANETS[z][1], z)
    arch(track.s_finish, "FINISH", (0.95, 0.95, 0.95), "finish")
    # chequered finish strip
    m_chk_b = principled("chk_b", (0.02, 0.02, 0.02), rough=0.5)
    m_chk_w = principled("chk_w", (0.95, 0.95, 0.95), rough=0.5)
    i = track.index_of_s(track.s_finish)
    q = frame_quat(track.T[i], track.UP[i])
    n_chk = 10; w_chk = 2 * track.A[i] / n_chk
    for k in range(n_chk):
        for row in range(2):
            l = -track.A[i] + w_chk * (k + 0.5)
            c = track.world(track.s_finish + (row - 0.5) * w_chk, l, 0.006)
            box_obj("chk", c, (w_chk, w_chk, 0.01), m_chk_b if (k + row) % 2 else m_chk_w, q, C_trk)
    # start gate (drops at gate time)
    ig = track.index_of_s(track.s_gate)
    gate = box_obj("StartGate", track.world(track.s_gate + 0.08, 0, 0.24),
                   (2 * track.A[ig] + 0.3, 0.12, 0.48), principled("gate", (0.9, 0.1, 0.1), rough=0.3),
                   frame_quat(track.T[ig], track.UP[ig]), C_trk)
    gate.keyframe_insert("location", frame=fr(D.gate) - 1)
    gate.location = Vector(gate.location) - Vector(track.UP[ig]) * 0.75
    gate.keyframe_insert("location", frame=fr(D.gate) + 3)

    # ------------------------------------------------------------- podium
    i_end = track.N - 1
    Tend = Vector(track.T[track.index_of_s(track.s_finish)]); Tend.z = 0; Tend.normalize()
    Lend = Vector((-Tend.y, Tend.x, 0))
    pod_c = Vector(track.P[track.index_of_s(track.s_finish + 6)]) + Lend * 6.0
    pod_c.z = gz
    pod_q = frame_quat(Lend, (0, 0, 1))         # podium faces -Lend (towards the track side)
    pod_heights = {0: 1.2, 1: 0.85, 2: 0.6}
    pod_x = {0: 0.0, 1: 1.15, 2: -1.15}        # 2nd on the viewer's left
    m_pod = [principled("pod_gold", (1.0, 0.72, 0.15), metallic=0.8, rough=0.25),
             principled("pod_silver", (0.8, 0.82, 0.86), metallic=0.8, rough=0.25),
             principled("pod_bronze", (0.72, 0.42, 0.2), metallic=0.8, rough=0.3)]
    face = -Lend
    side = Vector((face.y, -face.x, 0))           # podium's local "right"
    pod_top = {}
    for k in range(3):
        h = pod_heights[k]
        c = pod_c + side * pod_x[k] + Vector((0, 0, h / 2))
        box_obj("podium%d" % (k + 1), c, (1.1, 1.1, h), m_pod[k], frame_quat(face, (0, 0, 1)), C_env)
        pod_top[k] = pod_c + side * pod_x[k] + Vector((0, 0, h + r))
        t = text_obj("podnum", str(k + 1), 0.55, m_white, coll=C_env, bold=0.05)
        t.rotation_mode = "QUATERNION"
        t.rotation_quaternion = Matrix((-side, Vector((0, 0, 1)), face)).transposed().to_quaternion()
        t.location = pod_c + side * pod_x[k] + Vector((0, 0, h * 0.5)) + face * 0.56

    # ------------------------------------------------------------- marbles
    sph = bpy.data.meshes.new("marble")
    sv, sf = [], []
    nu, nv = 32, 16
    for j in range(nv + 1):
        th = math.pi * j / nv
        for i in range(nu):
            ph = 2 * math.pi * i / nu
            sv.append((r * math.sin(th) * math.cos(ph), r * math.sin(th) * math.sin(ph), r * math.cos(th)))
    for j in range(nv):
        for i in range(nu):
            a = j * nu + i; b = j * nu + (i + 1) % nu
            sf.append((a, b, b + nu, a + nu))
    marble_objs = []
    for k, (name, col, finish) in enumerate(MARBLES):
        if finish == "GLASS":
            mat = principled("marble_%s" % name, col, rough=0.05, transmission=0.9, coat=0.5)
        elif finish == "METAL":
            mat = principled("marble_%s" % name, col, metallic=1.0, rough=0.22)
        else:
            mat = principled("marble_%s" % name, col, rough=0.3, coat=1.0)
        me = bpy.data.meshes.new("marble_" + name)
        me.from_pydata(sv, [], sf); me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        me.materials.append(mat)
        ob = link(bpy.data.objects.new("Marble_%s" % name, me), C_mrb)
        ob.rotation_mode = "QUATERNION"
        # number decals on 2 sides (white disc + dark number)
        for sgn in (1, -1):
            disc = text_obj("num_%s" % name, name, 0.26, m_white if finish != "PAINT" or k not in (2,) else m_white,
                            coll=C_mrb, bold=0.06)
            disc.parent = ob
            disc.rotation_mode = "QUATERNION"
            # text normal (+Z local) -> marble local +/-X
            disc.rotation_quaternion = Quaternion((0, 1, 0), sgn * math.pi / 2) @ Quaternion((0, 0, 1), sgn * math.pi / 2)
            disc.location = (sgn * (r + 0.003), 0, 0)
            disc.data.extrude = 0.004
        marble_objs.append(ob)

    # ---- keyframe every frame from the baked sim
    def marble_state(f):
        tv = (f - 1) / fps
        mode, ts = D.mode_at(tv)
        return mode, ts, D.sample(ts)

    podium_rank = [m.idx for m in D.fin[:3]]
    t_key = time.time()
    states = [None] + [marble_state(f) for f in range(1, nF + 1)]
    for f in range(1, nF + 1):
        mode, ts, row = states[f]
        for k, ob in enumerate(marble_objs):
            p, q, s_, st, z_, sp = row[k]
            if mode == "podium" and k in podium_rank:
                pos = pod_top[podium_rank.index(k)]
                ob.location = pos
                ob.rotation_quaternion = Quaternion((0, 0, 1), 0.6 * (f / fps))
            else:
                ob.location = p
                ob.rotation_quaternion = q
            ob.keyframe_insert("location", frame=f)
            ob.keyframe_insert("rotation_quaternion", frame=f)
    print("keyed marbles in %.1f s" % (time.time() - t_key))

    # ------------------------------------------------------------- camera
    cam_d = bpy.data.cameras.new("Camera")
    cam_d.sensor_fit = "VERTICAL"; cam_d.sensor_height = 24.0; cam_d.lens = 22.0
    cam_d.clip_start = 0.02; cam_d.clip_end = 1000
    cam = link(bpy.data.objects.new("Camera", cam_d), C_env)
    sc.camera = cam
    cam.rotation_mode = "QUATERNION"
    half_h = 12.0 / cam_d.lens                  # half frame height at distance 1
    half_w = half_h * CONFIG["resolution"][0] / CONFIG["resolution"][1]

    def look(pos, tgt):
        d = Vector(tgt) - Vector(pos)
        return d.to_track_quat("-Z", "Y")

    def track_dir(s0):
        i = track.index_of_s(max(0.0, min(track.length, s0)))
        t = Vector(track.T[i]); t.z = 0
        return t.normalized()

    # cut-away windows (video time)
    cuts = []
    if "hairpin" in D.feat_t:
        i0 = track.feature["hairpin"][1]; i1 = track.feature_end["hairpin"][1]
        C = Vector((0, 0, 0))
        for j in range(i0, i1 + 1): C += Vector(track.P[j])
        C /= (i1 - i0 + 1)
        dirin = track_dir(track.feature["hairpin"][0])
        t0 = D.feat_t["hairpin"] + D.gate - 0.9
        cuts.append(("hairpin", t0, t0 + 4.2, C - dirin * 5.0 + Vector((0, 0, 6.5)), C + dirin * 0.5))
    if "gap" in D.feat_t:
        i0 = track.feature["gap"][1]; i1 = track.feature_end["gap"][1]
        C = (Vector(track.P[i0]) + Vector(track.P[i1])) / 2 + Vector(track.T[i1]) * 1.2
        Lg = Vector(track.LAT[i0]); Lg.z = 0; Lg.normalize()
        t0 = D.feat_t["gap"] + D.gate - 0.8
        take = Vector(track.P[i0]); Tg = Vector(track.T[i0]); Tg.z = 0; Tg.normalize()
        mid = take + Tg * 2.6 + Vector((0, 0, -0.1))
        cuts.append(("gap", t0, t0 + 4.8, mid + Lg * 11.0 + Vector((0, 0, 1.0)), mid + Vector((0, 0, -0.9))))
        # "1 m" drop ruler beside the landing
        land = Vector(track.P[i1])
        rp = land + Vector(track.LAT[i1]) * (track.A[i1] + track.RWS[i1] + 0.25)
        m_rul = emission_mat("ruler", (1, 1, 1), 1.5)
        drop = take.z - land.z
        box_obj("drop_ruler", rp + Vector((0, 0, drop / 2)), (0.05, 0.05, drop), m_rul, None, C_trk)
        for zz in (0.0, drop):
            box_obj("drop_tick", rp + Vector((0, 0, zz)), (0.3, 0.05, 0.04), m_rul, frame_quat(Tg, (0, 0, 1)), C_trk)
        rt = text_obj("drop_label", "%.1f m" % drop, 0.24, m_rul, align="CENTER", coll=C_trk, bold=0.04)
        rt.rotation_mode = "QUATERNION"
        rt.rotation_quaternion = Matrix((-Tg, Vector((0, 0, 1)), Lg)).transposed().to_quaternion()
        rt.location = rp + Vector((0, 0, drop + 0.25))

    i_f = track.index_of_s(track.s_finish)
    Lf = Vector(track.LAT[i_f]); Lf.z = 0; Lf.normalize()
    fin_pt = Vector(track.P[i_f]) + Vector((0, 0, 0.35))
    ig0 = track.index_of_s(track.s_gate)
    gate_pt = Vector(track.world(1.85, 0, 0.0))
    hook_pos0 = Vector(track.world(track.s_gate + 2.0, 0, 4.3))
    hook_pos1 = Vector(track.world(track.s_gate + 1.5, 0, 3.7))

    sm_pos = None; sm_tgt = None; sm_dir = None
    cam_log = []
    for f in range(1, nF + 1):
        tv = (f - 1) / fps
        mode, ts, row = states[f]
        if mode == "hook" or (mode == "live" and tv < D.gate + 0.25):
            u = smoothstep(0, D.gate + 0.25, tv)
            pos = hook_pos0.lerp(hook_pos1, u); tgt = gate_pt
            sm_pos = None
            cam_log.append((pos, tgt))
        elif mode == "live":
            order = D.rank(row)
            lead = next((k for k in order if row[k][3] != OUT), order[0])
            lp = Vector(row[lead][0]); ls = row[lead][2]
            pack = [Vector(row[k][0]) for k in range(len(row))
                    if row[k][3] != OUT and ls - row[k][2] < 9.0]
            pc = sum(pack, Vector((0, 0, 0))) / len(pack)
            tgt_raw = lp * 0.55 + pc * 0.45
            dir_raw = track_dir(ls + 1.5)
            if sm_pos is None:
                sm_tgt = tgt_raw.copy(); sm_dir = dir_raw.copy()
            a_t = 1 - math.exp(-1 / fps / 0.35); a_d = 1 - math.exp(-1 / fps / 0.7)
            sm_tgt = sm_tgt.lerp(tgt_raw, a_t)
            sm_dir = sm_dir.lerp(dir_raw, a_d).normalized()
            pos_raw = sm_tgt - sm_dir * 5.2 + Vector((0, 0, 4.2))
            if sm_pos is None:
                sm_pos = pos_raw.copy()
            sm_pos = sm_pos.lerp(pos_raw, 1 - math.exp(-1 / fps / 0.25))
            pos = sm_pos.copy(); tgt = sm_tgt + sm_dir * 1.6
            # blend in from the hook shot
            if tv < D.gate + 1.4:
                u = smoothstep(D.gate + 0.25, D.gate + 1.4, tv)
                pos = hook_pos1.lerp(pos, u); tgt = gate_pt.lerp(tgt, u)
            for name, c0, c1, cpos, ctgt in cuts:
                if c0 <= tv < c1:
                    pos, tgt = cpos, ctgt
            cam_log.append((pos, tgt))
        elif mode == "replay":
            u = (tv - D.live_end) / D.replay_len
            Tf = Vector(track.T[i_f])
            pos = fin_pt + Tf * lerp(3.0, 3.3, u) + Lf * 2.2 + Vector((0, 0, 1.9))
            tgt = fin_pt - Tf * lerp(1.6, 0.6, u) - Lf * 0.2
            cam_log.append((pos, tgt))
        else:
            u = (tv - D.replay_end) / max(0.1, 75.0 - D.replay_end)
            tgt = pod_c + Vector((0, 0, -0.2))
            pos = pod_c + face * lerp(6.4, 5.8, u) + Vector((0, 0, lerp(1.9, 1.7, u))) + side * lerp(-0.5, 0.5, u)
            cam_log.append((pos, tgt))
        cam.location = pos
        cam.rotation_quaternion = look(pos, tgt)
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_quaternion", frame=f)

    # ------------------------------------------------------------- HUD (parented to the camera)
    HD = 0.3          # HUD plane distance in front of the lens

    def hud(ob, x, y, scale=1.0):
        """x in [-1,1] across the frame width, y in [-1,1] up the frame height."""
        ob.parent = cam
        ob.location = (x * half_w * HD, y * half_h * HD, -HD)
        ob.scale = (HD * scale, HD * scale, HD * scale)
        no_shadow(ob)
        if ob.users_collection and ob.users_collection[0] != C_hud:
            for c in list(ob.users_collection): c.objects.unlink(ob)
            C_hud.objects.link(ob)
        return ob

    def plate(name, x, y, w, h, mat=m_plate, z=-0.002):
        v = [(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)]
        ob = mesh_obj(name, v, [(0, 1, 2, 3)], [mat], coll=C_hud)
        hud(ob, x, y)
        ob.location.z += z * HD
        return ob

    def caption(name, body, x, y, size, mat=m_white, plate_w=None, plate_h=None, interval=None,
                pmat=m_plate, align="CENTER"):
        t = text_obj(name, body, size, mat, align=align, coll=C_hud, bold=0.025)
        hud(t, x, y)
        objs = [t]
        bpy.context.view_layer.update()
        maxw = 2 * half_w * 0.9
        if t.dimensions.x / HD > maxw:             # auto-fit long lines
            k = maxw / (t.dimensions.x / HD)
            t.scale = (HD * k,) * 3
            size *= k
            bpy.context.view_layer.update()
        if plate_w is None:
            plate_w = t.dimensions.x / HD + size * 1.2
        if plate_h is None:
            plate_h = size * 1.6 * (body.count("\n") + 1)
        pxo = 0.0
        if align == "LEFT":
            pxo = (plate_w / 2 - size * 0.6) / (half_w)
        p = plate(name + "_plate", x + pxo, y, plate_w, plate_h, pmat)
        objs.append(p)
        if interval is not None:
            for o in objs:
                key_visible(o, [(fr(a), fr(b)) for a, b in interval], nF)
        return objs

    W = 2 * half_w          # frame width in HUD units (at distance 1)
    gate = D.gate
    zs_v = {zi: t + gate for zi, t in D.zone_t.items()}
    feat_v = {k: t + gate for k, t in D.feat_t.items()}
    live_end = D.live_end
    # -- hook
    caption("hook", "PICK YOUR MARBLE " + emoji("👇", "!"), 0, 0.80, 0.075, m_yellow, interval=[(0, gate + 0.2)])
    caption("hook2", "MARBLE LEAGUE · RACE THROUGH 5 PLANETS", 0, 0.66, 0.032, interval=[(0, gate + 0.2)])
    for n, num in enumerate(["3", "2", "1"]):
        t0 = n * gate / 3
        caption("count%s" % num, num, 0, -0.55, 0.22, m_yellow, plate_w=0.2, plate_h=0.26,
                interval=[(t0, t0 + gate / 3 - 1 / fps)])
    caption("off", "AND THEY'RE OFF!", 0, 0.80, 0.07, m_yellow, interval=[(gate, gate + 1.7)])
    # -- zone labels (top third), follow the leader's zone
    zone_iv = {}
    seq = sorted(zs_v.items(), key=lambda kv: kv[1])
    for n, (zi, t0) in enumerate(seq):
        t1 = seq[n + 1][1] if n + 1 < len(seq) else live_end
        zone_iv[zi] = [(max(t0, gate + 1.7) if zi == 0 else t0, t1 - 1 / fps)]
    for zi, z in enumerate(zo):
        if zi in zone_iv:
            gtxt = ("%g" % PLANETS[z][0])
            caption("zone_" + z, "%s · %s m/s²" % (z, gtxt), 0, 0.82, 0.07, m_white,
                    interval=zone_iv[zi])
    # -- commentary captions (beat sheet), timed from the baked race
    caps = []
    def cap(t0, dur, text, col=m_white):
        if t0 is None: return
        t1 = min(t0 + dur, live_end - 0.05)
        if t1 > t0: caps.append((t0, t1, text, col))
    eg = 9.81
    def rel(z): return PLANETS[z][0] / eg
    if 0 in zs_v:
        cap(gate + 1.8, 4.0, "Earth gravity. The pack bunches up")
    cap(feat_v.get("chicane"), 4.0, "Chicane: bumping for position!")
    if "MOON" in zo:
        zi = zo.index("MOON"); t = zs_v.get(zi)
        cap(t, 5.5, "1/6 of Earth: every bump = a floaty jump")
        cap(feat_v.get("wideturn"), 5.0, "Wide turn: low grip, the leader drifts wide")
    if "JUPITER" in zo:
        zi = zo.index("JUPITER"); t = zs_v.get(zi)
        cap(t, 3.5, "2.5x Earth gravity: everything gets heavy")
        cap(feat_v.get("hairpin"), 4.0, "Banked hairpin: too fast = over the wall")
    if "PLUTO" in zo:
        zi = zo.index("PLUTO"); t = zs_v.get(zi)
        cap(t, 3.0, "Pluto: 1/16 of Earth gravity")
        cap(feat_v.get("gap"), 3.4, "GAP JUMP: 1 m drop = 1.8 s in the air")
        if D.gap_hang and feat_v.get("gap"):
            k, hang = D.gap_hang
            cap(feat_v["gap"] + 3.5, 3.5, "#%s hang time: %.2f s" % (MARBLES[k][0], hang), m_yellow)
    if "SUN" in zo:
        zi = zo.index("SUN"); t = zs_v.get(zi)
        cap(t, 4.0, "SUN: 28x Earth gravity. Glued to the track!")
        cap(t + 4.0 if t else None, 3.5, "Final sprint!")
    if D.fin:
        cap(D.fin[0].finish_t + gate - 0.2, 3.0, "PHOTO FINISH!", m_yellow)
    caps.sort()
    # avoid overlaps: cut each caption at the start of the next
    for n in range(len(caps) - 1):
        if caps[n][1] > caps[n + 1][0]:
            caps[n] = (caps[n][0], caps[n + 1][0] - 1 / fps, caps[n][2], caps[n][3])
    for n, (t0, t1, text, col) in enumerate(caps):
        caption("cap%02d" % n, text, 0, 0.70, 0.04, col, interval=[(t0, t1)])
    # -- OUT pop-ups
    for m in sim["marbles"]:
        if m.out_t is not None and m.finish_t is None and m.out_reason != "time limit":
            t0 = m.out_t + gate
            if t0 < live_end:
                caption("out_%d" % m.idx, emoji("❌", "X") + " OUT  #%s" % MARBLES[m.idx][0], 0, -0.25, 0.075,
                        m_white, pmat=m_red_plate, interval=[(t0, min(t0 + 2.5, live_end))])
    # -- live position tower (left)
    rows = len(MARBLES)
    row_h = 0.062; top_y = 0.48
    tx = -0.80
    tower_iv = [(gate, live_end - 1 / fps)]
    for name, c0, c1, _, _ in cuts:              # cut-aways are clean shots: hide the tower
        new = []
        for a, b in tower_iv:
            if c1 <= a or c0 >= b:
                new.append((a, b))
            else:
                if c0 > a: new.append((a, c0 - 1 / fps))
                if c1 < b: new.append((c1, b))
        tower_iv = new
    tw = 0.34
    pl = plate("tower_plate", tx + tw / 2 / half_w - 0.06, top_y - (rows - 1) * row_h / 2 + 0.01,
               tw, (rows + 1.1) * row_h * half_h)
    key_visible(pl, [(fr(a), fr(b)) for a, b in tower_iv], nF)
    hdr = text_obj("tower_hdr", "LIVE", 0.026, m_yellow, align="LEFT", coll=C_hud, bold=0.03)
    hud(hdr, tx - 0.03, top_y + row_h * 0.95)
    key_visible(hdr, [(fr(a), fr(b)) for a, b in tower_iv], nF)
    for n in range(rows):
        t = text_obj("pos%d" % (n + 1), "%d" % (n + 1), 0.028, m_white, align="LEFT", coll=C_hud, bold=0.03)
        hud(t, tx - 0.03, top_y - n * row_h)
        key_visible(t, [(fr(a), fr(b)) for a, b in tower_iv], nF)
    tiv_f = [(fr(a), fr(b)) for a, b in tower_iv]

    def isect(A, B):
        return [(max(a0, b0), min(a1, b1)) for a0, a1 in A for b0, b1 in B if min(a1, b1) >= max(a0, b0)]
    tags = []
    for k, (name, col, _) in enumerate(MARBLES):
        chip = mesh_obj("tag_chip_%s" % name,
                        [(-0.012, -0.012, 0), (0.012, -0.012, 0), (0.012, 0.012, 0), (-0.012, 0.012, 0)],
                        [(0, 1, 2, 3)], [emission_mat("chip_%s" % name, col, 1.0)], coll=C_hud)
        hud(chip, 0, 0)
        txt = text_obj("tag_txt_%s" % name, "#%s" % name, 0.028, m_white, align="LEFT", coll=C_hud, bold=0.03)
        hud(txt, 0, 0)
        outt = text_obj("tag_out_%s" % name, "OUT", 0.022, m_red, align="LEFT", coll=C_hud, bold=0.03)
        hud(outt, 0, 0)
        fint = text_obj("tag_fin_%s" % name, emoji("🏁", "F"), 0.022, m_white, align="LEFT", coll=C_hud)
        hud(fint, 0, 0)
        tags.append((chip, txt, outt, fint))
        m = sim["marbles"][k]
        key_visible(chip, [(fr(a), fr(b)) for a, b in tower_iv], nF)
        key_visible(txt, [(fr(a), fr(b)) for a, b in tower_iv], nF)
        if m.finish_t is None and m.out_t is not None:
            key_visible(outt, isect([(fr(m.out_t + gate), fr(live_end) - 1)], tiv_f), nF)
        else:
            key_visible(outt, [], nF)
        if m.finish_t is not None:
            key_visible(fint, isect([(fr(m.finish_t + gate), fr(live_end) - 1)], tiv_f), nF)
        else:
            key_visible(fint, [], nF)
    ypos = [None] * rows
    for f in range(fr(gate), fr(live_end)):
        mode, ts, row = states[f]
        order = D.rank(row)
        for slot, k in enumerate(order):
            target = top_y - slot * row_h
            ypos[k] = target if ypos[k] is None else ypos[k] + (target - ypos[k]) * (1 - math.exp(-1 / fps / 0.12))
            chip, txt, outt, fint = tags[k]
            y = ypos[k]
            for ob, x in ((chip, tx + 0.13), (txt, tx + 0.21), (outt, tx + 0.55), (fint, tx + 0.55)):
                ob.location = (x * half_w * HD, y * half_h * HD, -HD)
                ob.keyframe_insert("location", frame=f)
    # -- Sun speed read-out (one text object per distinct value, keyed visibility)
    if "SUN" in zo and zo.index("SUN") in zs_v:
        t0 = zs_v[zo.index("SUN")]
        vals = {}
        for f in range(fr(t0), fr(live_end)):
            mode, ts, row = states[f]
            order = D.rank(row)
            lead = next((k for k in order if row[k][3] == RACING), None)
            if lead is None:
                continue
            kmh = int(round(row[lead][5] * 3.6))
            vals.setdefault((lead, kmh), []).append(f)
        caption("speed_lbl", "LEADER SPEED", 0, -0.62, 0.03, m_white, plate_w=0.42, plate_h=0.16,
                interval=[(t0, live_end - 1 / fps)])
        for (lead, kmh), frs in vals.items():
            ivs = []; a = frs[0]; b = frs[0]
            for f in frs[1:]:
                if f == b + 1: b = f
                else: ivs.append((a, b)); a = b = f
            ivs.append((a, b))
            t = text_obj("speed_%s_%d" % (MARBLES[lead][0], kmh), "#%s  %d km/h" % (MARBLES[lead][0], kmh),
                         0.05, m_yellow, coll=C_hud, bold=0.03)
            hud(t, 0, -0.70)
            key_visible(t, ivs, nF)
    # -- replay
    caption("replay", "SLOW-MO REPLAY  x%.2f" % D.slowmo, 0, 0.82, 0.05, m_yellow,
            interval=[(live_end, D.replay_end - 1 / fps)])
    caption("replay2", "PHOTO FINISH", 0, 0.70, 0.04, m_white, interval=[(live_end, D.replay_end - 1 / fps)])
    # -- podium + standings
    end_iv = [(D.replay_end, 75.0)]
    medals = [emoji("🥇", "1st"), emoji("🥈", "2nd"), emoji("🥉", "3rd")]
    if D.fin:
        pod_txt = "   ".join("%s #%s" % (medals[n], MARBLES[m.idx][0]) for n, m in enumerate(D.fin[:3]))
        caption("podium_txt", pod_txt, 0, 0.84, 0.06, m_yellow, interval=end_iv)
    lines_pos, lines_num, lines_time = [], [], []
    for n, m in enumerate(D.fin):
        lines_pos.append("%d" % (n + 1)); lines_num.append("#%s" % MARBLES[m.idx][0])
        lines_time.append("%.2f s" % (m.finish_t + gate) if n == 0 else "+%.2f s" % (m.finish_t - D.fin[0].finish_t))
    for m in sim["dnf"]:
        lines_pos.append("-"); lines_num.append("#%s" % MARBLES[m.idx][0])
        lines_time.append("OUT (%s)" % zo[m.out_zone].title() if m.out_zone is not None else "DNF")
    tbl_y = -0.08; size = 0.034
    th = text_obj("table_hdr", "STANDINGS", 0.03, m_yellow, coll=C_hud, bold=0.03)
    hud(th, 0, tbl_y + 0.03)
    key_visible(th, [(fr(a), fr(b)) for a, b in end_iv], nF)
    col_h = 0.0
    for col_txt, x, al in (("\n".join(lines_pos), -0.62, "LEFT"), ("\n".join(lines_num), -0.38, "LEFT"),
                           ("\n".join(lines_time), 0.05, "LEFT")):
        t = text_obj("table_col", col_txt, size, m_white, align=al, coll=C_hud, bold=0.025)
        t.data.align_y = "TOP"
        hud(t, x, tbl_y - 0.05)
        key_visible(t, [(fr(a), fr(b)) for a, b in end_iv], nF)
        bpy.context.view_layer.update()
        col_h = max(col_h, t.dimensions.y / HD)
    top = (tbl_y + 0.03) * half_h + 0.03            # absolute HUD units
    bot = (tbl_y - 0.05) * half_h - col_h - 0.015
    tp = plate("table_plate", 0, (top + bot) / 2 / half_h, 2 * half_w * 0.86, top - bot)
    key_visible(tp, [(fr(a), fr(b)) for a, b in end_iv], nF)
    caption("next", "Next race: Mars Canyon. Pick again " + emoji("👇", ""), 0, -0.80, 0.042, m_yellow,
            interval=end_iv)
    print("scene built in %.1f s" % (time.time() - t_build))
    return D


def render_frames(frames, scale=None):
    sc = bpy.context.scene
    out = bpy.path.abspath(CONFIG["output_dir"])
    os.makedirs(out, exist_ok=True)
    ims = sc.render.image_settings
    try:
        if hasattr(ims, "media_type"):
            ims.media_type = "IMAGE"
        ims.file_format = "PNG"
    except Exception as e:
        print("PNG setup:", e)
    if scale:
        sc.render.resolution_percentage = scale
    for f in frames:
        sc.frame_set(f)
        sc.render.filepath = os.path.join(out, "frame_%04d.png" % f)
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        print("rendered frame %d in %.1f s -> %s" % (f, time.time() - t0, sc.render.filepath))


def forcefield_probe():
    """The prototype that ruled out Blender force fields (run with --ff-test).

    Scene gravity off, one rigid-body sphere (1 kg), one force field asking
    for the Moon's 1.62 m/s².  Prints the acceleration Bullet actually gives."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, 60
    sc.use_gravity = False
    bpy.ops.rigidbody.world_add()
    rw = sc.rigidbody_world
    rw.substeps_per_frame = 60; rw.solver_iterations = 20; rw.point_cache.frame_end = 60
    for ftype, shape in (("FORCE", "PLANE"), ("WIND", "PLANE"), ("FORCE", "POINT")):
        for ob in list(sc.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.ops.object.effector_add(type=ftype, location=(0, 0, 50))
        fs = bpy.context.object.field
        fs.shape = shape; fs.strength = 1.62; fs.flow = 0; fs.falloff_type = "TUBE"
        fs.use_radial_max = True; fs.radial_max = 5.0
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3, location=(0, 0, 40))
        b = bpy.context.object
        bpy.ops.rigidbody.object_add(); b.rigid_body.mass = 1.0; b.rigid_body.linear_damping = 0
        rw.point_cache.frame_end = 60
        bpy.ops.ptcache.free_bake_all()
        zs = []
        for f in range(1, 61):
            sc.frame_set(f); zs.append(b.matrix_world.translation.z)
        acc = [(zs[i + 1] - 2 * zs[i] + zs[i - 1]) * 900 for i in range(5, 58, 8)]
        print("force field %-5s %-5s asked 1.62 m/s² down -> Bullet gives a_z = %s"
              % (ftype, shape, ", ".join("%.3f" % a for a in acc)))


def main():
    opts = parse_args()
    if opts.get("ff_test") and HAVE_BPY:
        forcefield_probe()
        return
    track, sim = run_physics()
    if opts["sim_only"] or not HAVE_BPY:
        return
    build_scene(track, sim)
    bpy.context.scene.frame_set(1)
    if opts.get("frames"):
        render_frames(opts["frames"], opts.get("scale"))
    elif CONFIG["render_on_run"]:
        t0 = time.time()
        bpy.ops.render.render(animation=True)
        print("rendered animation in %.1f min" % ((time.time() - t0) / 60))


if __name__ == "__main__" or HAVE_BPY:
    main()
