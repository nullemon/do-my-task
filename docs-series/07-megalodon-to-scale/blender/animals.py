"""MEGALODON TO SCALE — procedural low-detail animal models + swim-cycle sprite loops (Blender 5.1.2 bpy, Cycles CPU).

Every animal is built from numbers (body-depth / body-width profiles along its length, fin outlines in
body-length units) and rendered by an ORTHOGRAPHIC side camera (tilted 12 deg to look slightly up from below),
so horizontal lengths are exact. One seamless tail-beat loop per species is rendered with a transparent film;
the compositor (comp.py) places the loops in the ocean at true relative scale (px_per_m from meta.json).
Shading is emission-only (top light + side fill + cool rim computed from the normal) -> no lights, no bounces.

Run: /home/user/bpyenv/bin/python -c "import sys; p='blender/animals.py'; sys.argv=['blender','--','SPECIES[,..]|all',
     '[--test]']; exec(compile(open(p).read(),p,'exec'))"
"""
import bpy, os, sys, math, json
import numpy as np

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/07-megalodon-to-scale"
OUTD = os.path.join(SCR, "sprites")
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
WHICH = argv[0] if argv else "all"
TEST = "--test" in argv
TILT = 12.0           # camera looks up from slightly below (deg); x-lengths are exact in orthographic view
LIGHT = np.array([0.25, -0.45, 1.0]); LIGHT /= np.linalg.norm(LIGHT)


# ----------------------------------------------------------------------------- small numeric helpers
def pchip(xs, ys, x):
    """Monotone cubic (Fritsch-Carlson) interpolation."""
    xs = np.asarray(xs, float); ys = np.asarray(ys, float); x = np.asarray(x, float)
    h = np.diff(xs); d = np.diff(ys) / h
    m = np.zeros_like(ys)
    m[1:-1] = np.where(d[:-1] * d[1:] > 0, 3 * (h[:-1] + h[1:]) / ((2 * h[1:] + h[:-1]) / d[:-1] + (h[1:] + 2 * h[:-1]) / d[1:]), 0)
    m[0] = d[0]; m[-1] = d[-1]
    i = np.clip(np.searchsorted(xs, x) - 1, 0, len(h) - 1)
    t = (x - xs[i]) / h[i]
    h00 = 2 * t**3 - 3 * t**2 + 1; h10 = t**3 - 2 * t**2 + t; h01 = -2 * t**3 + 3 * t**2; h11 = t**3 - t**2
    return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


# ----------------------------------------------------------------------------- species definitions
# Units: fractions of total length L. s = 0 at the snout, 1 at the tip of the tail fin.
# body: (s, half_depth_top, half_depth_bottom, half_width, centre_z); body ends at s_end (caudal peduncle / fluke root).
# fins: median (in the x-z plane) outlines as (s, z) points; paired fins: root s, root height, outline in (chord, span).
SPECIES = {}

def shark_body(depth=0.11, width=0.085, s_end=0.80, head_z=-0.004, snout=0.035, girth_at=0.32):
    return dict(
        s=[0, 0.012, snout, 0.10, 0.20, girth_at, 0.45, 0.60, 0.72, s_end],
        top=[0, depth * .22, depth * .45, depth * .78, depth * .96, depth, depth * .9, depth * .62, depth * .34, depth * .16],
        bot=[0, depth * .14, depth * .38, depth * .74, depth * .92, depth * .98, depth * .86, depth * .55, depth * .3, depth * .15],
        wid=[0, width * .25, width * .5, width * .82, width * .97, width, width * .9, width * .6, width * .34, width * .16],
        zc=[head_z, head_z, head_z * .6, 0, 0, 0, 0, 0, 0, 0.01], s_end=s_end)

# great white: stout, fusiform; near-lunate tail; big first dorsal; tiny 2nd dorsal/anal; heavy keel
SPECIES["gw"] = dict(
    L=6.0, cycle=1.5, kind="shark", lat=0.075, lam=0.95, tex="gw",
    body=shark_body(depth=0.115, width=0.095, s_end=0.80, girth_at=0.36),
    median=[
        ("dorsal", [(0.33, 0.10), (0.38, 0.215), (0.405, 0.225), (0.43, 0.20), (0.47, 0.085)]),
        ("dorsal2", [(0.69, 0.035), (0.705, 0.06), (0.72, 0.03)]),
        ("anal", [(0.70, -0.03), (0.715, -0.055), (0.73, -0.026)]),
        ("caudal", [(0.78, 0.02), (0.86, 0.12), (0.935, 0.255), (0.96, 0.27), (0.925, 0.16), (0.90, 0.07), (0.885, 0.0),
                    (0.905, -0.07), (0.94, -0.19), (0.92, -0.20), (0.86, -0.10), (0.78, -0.018)]),
    ],
    paired=[
        ("pectoral", 0.24, -0.06, 0.32, [(0, 0), (0.09, 0), (0.12, 0.05), (0.16, 0.20), (0.135, 0.205), (0.05, 0.08)]),
        ("pelvic", 0.57, -0.07, 0.75, [(0, 0), (0.04, 0), (0.07, 0.045), (0.05, 0.05)]),
    ])
# bull shark: stocky, blunt rounded snout, big triangular first dorsal, larger 2nd dorsal, classic heterocercal tail
SPECIES["bull"] = dict(
    L=3.3, cycle=1.1, kind="shark", lat=0.085, lam=0.9, tex="bull",
    body=shark_body(depth=0.105, width=0.09, s_end=0.73, snout=0.03, girth_at=0.30),
    median=[
        ("dorsal", [(0.28, 0.095), (0.32, 0.20), (0.345, 0.205), (0.37, 0.17), (0.42, 0.08)]),
        ("dorsal2", [(0.60, 0.05), (0.625, 0.085), (0.66, 0.06), (0.665, 0.04)]),
        ("anal", [(0.61, -0.045), (0.635, -0.075), (0.66, -0.05)]),
        ("caudal", [(0.71, 0.015), (0.80, 0.07), (0.92, 0.165), (0.99, 0.20), (0.985, 0.17), (0.93, 0.10), (0.87, 0.02),
                    (0.84, -0.02), (0.83, -0.075), (0.80, -0.11), (0.78, -0.10), (0.75, -0.03), (0.71, -0.012)]),
    ],
    paired=[
        ("pectoral", 0.22, -0.06, 0.3, [(0, 0), (0.10, 0), (0.13, 0.06), (0.17, 0.19), (0.14, 0.195), (0.05, 0.09)]),
        ("pelvic", 0.52, -0.07, 0.75, [(0, 0), (0.045, 0), (0.075, 0.05), (0.055, 0.055)]),
    ])
# megalodon (2024-2025 slender interpretation, lemon-shark-like): long body, short blunt head, big pectorals,
# large second dorsal like a lemon shark, crescent-shaped tail. Fin shapes are UNKNOWN - schematic.
SPECIES["mega"] = dict(
    L=16.4, cycle=3.0, kind="shark", lat=0.06, lam=1.0, tex="mega",
    body=dict(
        s=[0, 0.012, 0.035, 0.09, 0.18, 0.30, 0.45, 0.60, 0.72, 0.80],
        top=[0, .02, .043, .066, .079, .082, .076, .056, .032, .016],
        bot=[0, .015, .038, .064, .077, .080, .07, .048, .028, .015],
        wid=[0, .02, .04, .058, .07, .072, .066, .048, .028, .014],
        zc=[-.004, -.004, -.002, 0, 0, 0, 0, 0, 0, .008], s_end=0.80),
    median=[
        ("dorsal", [(0.30, 0.075), (0.345, 0.165), (0.37, 0.172), (0.39, 0.15), (0.43, 0.07)]),
        ("dorsal2", [(0.60, 0.05), (0.63, 0.105), (0.655, 0.105), (0.67, 0.045)]),
        ("anal", [(0.62, -0.045), (0.645, -0.09), (0.67, -0.085), (0.68, -0.04)]),
        ("caudal", [(0.78, 0.014), (0.85, 0.08), (0.94, 0.19), (0.975, 0.205), (0.95, 0.13), (0.91, 0.05), (0.895, 0.0),
                    (0.91, -0.05), (0.94, -0.14), (0.92, -0.15), (0.86, -0.08), (0.78, -0.014)]),
    ],
    paired=[
        ("pectoral", 0.20, -0.05, 0.3, [(0, 0), (0.08, 0), (0.11, 0.05), (0.15, 0.16), (0.125, 0.165), (0.045, 0.07)]),
        ("pelvic", 0.54, -0.055, 0.75, [(0, 0), (0.04, 0), (0.065, 0.04), (0.05, 0.045)]),
    ])
# whale shark: broad flat head with terminal mouth, ridges, tall dorsal, big tail; spots via texture
SPECIES["whaleshark"] = dict(
    L=12.0, cycle=3.2, kind="shark", lat=0.06, lam=1.0, tex="whaleshark",
    body=dict(
        s=[0, 0.006, 0.03, 0.10, 0.22, 0.34, 0.48, 0.60, 0.70, 0.78],
        top=[0.02, .035, .055, .078, .092, .093, .08, .055, .032, .016],
        bot=[0.02, .03, .045, .07, .085, .085, .07, .05, .03, .015],
        wid=[0.04, .055, .075, .10, .11, .105, .085, .055, .03, .015],
        zc=[0, 0, 0, 0, 0, 0, 0, 0, 0, .006], s_end=0.78),
    median=[
        ("dorsal", [(0.38, 0.085), (0.43, 0.165), (0.455, 0.17), (0.47, 0.15), (0.51, 0.07)]),
        ("dorsal2", [(0.66, 0.04), (0.68, 0.07), (0.70, 0.04)]),
        ("anal", [(0.67, -0.035), (0.69, -0.06), (0.71, -0.035)]),
        ("caudal", [(0.76, 0.014), (0.84, 0.08), (0.95, 0.2), (0.985, 0.215), (0.95, 0.13), (0.90, 0.05), (0.875, 0.0),
                    (0.89, -0.05), (0.915, -0.12), (0.895, -0.13), (0.84, -0.07), (0.76, -0.012)]),
    ],
    paired=[
        ("pectoral", 0.22, -0.06, 0.28, [(0, 0), (0.09, 0), (0.12, 0.05), (0.15, 0.17), (0.125, 0.175), (0.04, 0.07)]),
        ("pelvic", 0.58, -0.06, 0.75, [(0, 0), (0.035, 0), (0.06, 0.04), (0.045, 0.045)]),
    ])
# orca: robust, rounded head, very tall male dorsal, paddle flippers, horizontal flukes (vertical undulation)
SPECIES["orca"] = dict(
    L=8.0, cycle=2.0, kind="whale", vert=0.05, lam=1.1, tex="orca",
    body=dict(
        s=[0, 0.015, 0.05, 0.12, 0.25, 0.38, 0.52, 0.66, 0.78, 0.86, 0.90],
        top=[0, .045, .075, .096, .11, .11, .098, .072, .045, .028, .015],
        bot=[0, .03, .062, .09, .105, .105, .09, .06, .034, .02, .012],
        wid=[0, .04, .07, .09, .102, .10, .088, .06, .034, .02, .012],
        zc=[-.01, -.01, -.005, 0, 0, 0, 0, 0, .005, .005, .005], s_end=0.90),
    median=[("dorsal", [(0.38, 0.10), (0.395, 0.24), (0.405, 0.30), (0.42, 0.29), (0.44, 0.17), (0.48, 0.09)])],
    paired=[
        ("flipper", 0.22, -0.07, 0.62, [(0, 0), (0.07, 0), (0.095, 0.06), (0.085, 0.11), (0.055, 0.125), (0.02, 0.08)]),
        ("fluke", 0.88, 0.0, 0.0, [(0, 0), (0.03, 0), (0.11, 0.11), (0.115, 0.13), (0.08, 0.12), (0.03, 0.05)]),
    ])
# humpback: long, knobby head, small hump dorsal, very long pectoral flippers (~1/3 body length), broad flukes
SPECIES["humpback"] = dict(
    L=15.0, cycle=3.6, kind="whale", vert=0.04, lam=1.2, tex="humpback",
    body=dict(
        s=[0, 0.02, 0.06, 0.15, 0.28, 0.40, 0.52, 0.64, 0.76, 0.86, 0.91],
        top=[0, .03, .055, .075, .092, .098, .088, .066, .04, .024, .012],
        bot=[0, .03, .06, .09, .10, .098, .08, .052, .03, .018, .01],
        wid=[0, .03, .06, .085, .10, .10, .085, .058, .033, .018, .01],
        zc=[-.012, -.012, -.008, -.004, 0, 0, 0, 0, .004, .005, .005], s_end=0.91),
    median=[("dorsal", [(0.60, 0.064), (0.625, 0.085), (0.64, 0.088), (0.66, 0.06)])],
    paired=[
        ("flipper", 0.27, -0.08, 0.75, [(0, 0), (0.07, 0), (0.13, 0.08), (0.19, 0.22), (0.215, 0.31), (0.185, 0.30), (0.10, 0.20), (0.04, 0.10), (0.0, 0.03)]),
        ("fluke", 0.895, 0.0, 0.0, [(0, 0), (0.03, 0), (0.10, 0.10), (0.12, 0.16), (0.09, 0.15), (0.04, 0.07)]),
    ])
# blue whale: very long, slender, flat broad head, tiny dorsal far back, small flippers
SPECIES["blue"] = dict(
    L=29.9, cycle=4.0, kind="whale", vert=0.035, lam=1.2, tex="blue",
    body=dict(
        s=[0, 0.02, 0.06, 0.15, 0.28, 0.42, 0.56, 0.68, 0.78, 0.87, 0.92],
        top=[0, .02, .036, .052, .062, .064, .058, .045, .03, .018, .009],
        bot=[0, .022, .045, .062, .068, .064, .052, .036, .022, .013, .008],
        wid=[0, .03, .05, .066, .074, .07, .06, .042, .026, .014, .008],
        zc=[-.006, -.006, -.004, -.002, 0, 0, 0, 0, .002, .003, .003], s_end=0.92),
    median=[("dorsal", [(0.74, 0.026), (0.765, 0.045), (0.775, 0.047), (0.78, 0.024)])],
    paired=[
        ("flipper", 0.25, -0.05, 0.7, [(0, 0), (0.035, 0), (0.07, 0.07), (0.075, 0.09), (0.06, 0.09), (0.015, 0.03)]),
        ("fluke", 0.915, 0.0, 0.0, [(0, 0), (0.02, 0), (0.07, 0.07), (0.08, 0.10), (0.06, 0.095), (0.025, 0.04)]),
    ])
# Perucetus colossus (basilosaurid, known only from partial postcranial skeleton): ghost reconstruction.
SPECIES["perucetus"] = dict(
    L=17.0, cycle=4.0, kind="whale", vert=0.03, lam=1.2, tex="peru", frames=1,
    body=dict(
        s=[0, 0.03, 0.08, 0.16, 0.30, 0.45, 0.60, 0.74, 0.86, 0.94],
        top=[0, .022, .04, .058, .072, .075, .066, .046, .026, .012],
        bot=[0, .02, .04, .06, .076, .078, .066, .044, .024, .011],
        wid=[0, .022, .045, .065, .08, .082, .07, .048, .026, .012],
        zc=[-.004] * 3 + [0] * 7, s_end=0.94),
    median=[],
    paired=[
        ("flipper", 0.16, -0.05, 0.7, [(0, 0), (0.03, 0), (0.06, 0.05), (0.05, 0.07), (0.02, 0.03)]),
        ("fluke", 0.93, 0.0, 0.0, [(0, 0), (0.02, 0), (0.05, 0.05), (0.055, 0.07), (0.035, 0.06)]),
    ])


# ----------------------------------------------------------------------------- textures (numpy, (u along length, v around))
def make_texture(kind, nu=1024, nv=256):
    u = (np.arange(nu) + 0.5) / nu
    v = (np.arange(nv) + 0.5) / nv
    U, V = np.meshgrid(u, v)                 # shape (nv, nu)
    th = V * 2 * np.pi                      # 0 = dorsal line, pi = belly
    c = np.cos(th); side = np.abs(np.sin(th))
    rng = np.random.default_rng(abs(hash(kind)) % 2**31)
    def noise(scale, oct=3):
        out = np.zeros_like(U)
        for o in range(oct):
            k = scale * 2**o
            g = rng.standard_normal((int(k * 0.7) + 3, int(k) + 3))
            from_y = V * (g.shape[0] - 3); from_x = U * (g.shape[1] - 3)
            iy = from_y.astype(int); ix = from_x.astype(int); fy = from_y - iy; fx = from_x - ix
            fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
            a = g[iy, ix] * (1 - fx) + g[iy, ix + 1] * fx; b = g[iy + 1, ix] * (1 - fx) + g[iy + 1, ix + 1] * fx
            out += (a * (1 - fy) + b * fy) / 2**o
        return out
    def col(r, g, b): return np.array([r, g, b], float)
    def mix(a, b, t): return a * (1 - t[..., None]) + b * t[..., None]
    T = lambda x: np.broadcast_to(x, U.shape)
    if kind in ("gw", "bull", "mega"):
        back = {"gw": col(.30, .33, .36), "bull": col(.36, .37, .37), "mega": col(.22, .25, .29)}[kind]
        belly = {"gw": col(.88, .88, .86), "bull": col(.75, .75, .72), "mega": col(.66, .68, .69)}[kind]
        edge = -0.05 + 0.07 * noise(5, 2) + (0.12 if kind == "gw" else 0.0) * smoothstep(0.1, 0.2, U) * (1 - smoothstep(0.6, 0.75, U))
        sharp = 0.05 if kind == "gw" else 0.18
        t = smoothstep(edge + sharp, edge - sharp, c)
        img = mix(np.broadcast_to(back, U.shape + (3,)), np.broadcast_to(belly, U.shape + (3,)), t)
        img *= (1 + 0.04 * noise(12, 2))[..., None]
    elif kind == "whaleshark":
        back = col(.17, .22, .28); belly = col(.78, .80, .80)
        t = smoothstep(0.05, -0.25, c)
        img = mix(np.broadcast_to(back, U.shape + (3,)), np.broadcast_to(belly, U.shape + (3,)), t)
        # pale spots on a jittered grid between thin pale vertical stripes (spots smaller towards the head)
        img = img.copy(); spotm = np.zeros(U.shape)
        r2 = np.random.default_rng(7)
        nu_c, nv_c = 70, 26
        for i in range(nu_c):
            for j in range(nv_c):
                cu = (i + 0.5 + r2.uniform(-.3, .3)) / nu_c; cv = (j + 0.5 + r2.uniform(-.3, .3)) / nv_c * 0.96
                rad = (0.0045 + 0.003 * smoothstep(0.05, 0.3, cu)) * r2.uniform(0.7, 1.2)
                du = U - cu; dv = (V - cv) * 0.45
                spotm = np.maximum(spotm, smoothstep(rad, rad * 0.6, np.sqrt(du * du + dv * dv)))
        stripe = smoothstep(0.0016, 0.0006, np.abs(((U * nu_c / 2.3) % 1.0) - 0.5) / (nu_c / 2.3)) * (U > 0.1)
        m = np.clip(spotm + 0.7 * stripe, 0, 1) * (1 - t) * (U < 0.8)
        img = mix(img, np.broadcast_to(col(.72, .76, .77), U.shape + (3,)), m)
    elif kind == "orca":
        black = col(.035, .04, .05); white = col(.92, .93, .92); grey = col(.42, .44, .46)
        img = np.broadcast_to(black, U.shape + (3,)).copy()
        # white chin + belly band (narrowing backwards), flank lobe sweeping up behind the dorsal fin
        bel_edge = -0.30 - 0.25 * smoothstep(0.30, 0.55, U)
        bel = smoothstep(bel_edge + 0.06, bel_edge - 0.06, c) * smoothstep(0.015, 0.05, U) * (1 - smoothstep(0.56, 0.64, U))
        fl = ((U - 0.62) / 0.07) ** 2 + ((c + 0.30 - 3.0 * (U - 0.62)) / 0.45) ** 2
        lobe = smoothstep(1.0, 0.75, fl) * smoothstep(0.1, 0.4, side)
        img = mix(img, np.broadcast_to(white, U.shape + (3,)), np.clip(bel + lobe, 0, 1))
        # eye patch: slanted oval above and behind the eye
        ep = ((U - 0.14) / 0.05) ** 2 + ((c - 0.30 + 1.5 * (U - 0.14)) / 0.10) ** 2
        img = mix(img, np.broadcast_to(white, U.shape + (3,)), smoothstep(1.0, 0.7, ep) * smoothstep(0.2, 0.5, side))
        # grey saddle behind dorsal
        sad = ((U - 0.47) / 0.06) ** 2 + ((c - 0.92) / 0.12) ** 2
        img = mix(img, np.broadcast_to(grey, U.shape + (3,)), smoothstep(1.0, 0.6, sad) * 0.8)
    elif kind == "humpback":
        back = col(.07, .08, .10); belly = col(.62, .64, .64)
        t = smoothstep(-0.2, -0.6, c) * (0.6 + 0.4 * np.clip(noise(12), -1, 1))
        img = mix(np.broadcast_to(back, U.shape + (3,)), np.broadcast_to(belly, U.shape + (3,)), np.clip(t, 0, 1))
        grooves = (np.sin(V * 256 * 1.2) > 0.6) * smoothstep(-0.4, -0.7, c) * (U < 0.48) * 0.5
        img *= (1 - 0.6 * grooves)[..., None]
    elif kind == "blue":
        base = col(.34, .42, .52); dark = col(.20, .26, .34)
        m = np.clip(0.5 + 0.6 * noise(30), 0, 1)
        img = mix(np.broadcast_to(base, U.shape + (3,)), np.broadcast_to(dark, U.shape + (3,)), m)
        img = mix(img, np.broadcast_to(col(.52, .58, .64), U.shape + (3,)), smoothstep(-0.3, -0.8, c) * 0.5)
    else:  # peru / generic
        img = np.broadcast_to(col(.30, .32, .34), U.shape + (3,)).copy()
    # reserved strip v in [0.97,1]: fin colour patches by u: [0,.25) dark, [.25,.5) light/white, [.5,.75) mid
    strip = V > 0.97
    finc = {"orca": (black if kind == "orca" else None)}
    dark_c = img[int(nv * 0.02), int(nu * 0.4)].copy()
    light_c = {"humpback": col(.85, .86, .86), "orca": col(.04, .04, .05)}.get(kind, img[int(nv * 0.5), int(nu * 0.3)].copy())
    mid_c = (dark_c * 0.6 + light_c * 0.4)
    for a, b, cc in ((0, .25, dark_c), (.25, .5, light_c), (.5, .75, mid_c)):
        msk = strip & (U >= a) & (U < b)
        img[msk] = cc
    return np.clip(img, 0, 1)

FIN_UV = {"dark": (0.12, 0.985), "light": (0.37, 0.985), "mid": (0.62, 0.985)}


# ----------------------------------------------------------------------------- mesh builders
def build_body(sp, nr=220, nt=40):
    L = sp["L"]; b = sp["body"]
    s = np.linspace(0, b["s_end"], nr)
    s = b["s_end"] * (1 - np.cos(np.linspace(0, np.pi / 2, nr)) ** 1.0) if False else s
    top = pchip(b["s"], b["top"], s) * L; bot = pchip(b["s"], b["bot"], s) * L
    wid = pchip(b["s"], b["wid"], s) * L; zc = pchip(b["s"], b["zc"], s) * L
    th = np.linspace(0, 2 * np.pi, nt, endpoint=False)
    c = np.cos(th); sn = np.sin(th)
    p = 2.4                                         # superellipse cross-section (slightly boxy)
    ce = np.sign(c) * np.abs(c) ** (2 / p); se = np.sign(sn) * np.abs(sn) ** (2 / p)
    hz = np.where(c[None, :] >= 0, top[:, None], bot[:, None])
    X = np.repeat(-s[:, None] * L, nt, 1)
    Y = wid[:, None] * se[None, :]
    Z = zc[:, None] + hz * ce[None, :]
    verts = np.stack([X, Y, Z], -1).reshape(-1, 3)
    uv = np.stack([np.repeat(s[:, None], nt, 1), np.repeat((th / (2 * np.pi))[None, :] * 0.96, nr, 0)], -1).reshape(-1, 2)
    faces = []; fuv = []
    for i in range(nr - 1):
        for j in range(nt):
            a = i * nt + j; bb = i * nt + (j + 1) % nt; cc = (i + 1) * nt + (j + 1) % nt; d = (i + 1) * nt + j
            faces.append((a, d, cc, bb))
            ua = uv[a].copy(); ub = uv[bb].copy(); uc = uv[cc].copy(); ud = uv[d].copy()
            if j == nt - 1: ub[1] = uc[1] = 0.96
            fuv.append((ua, ud, uc, ub))
    # tail cap
    base = (nr - 1) * nt
    faces.append(tuple(base + j for j in range(nt))[::-1]); fuv.append(tuple(uv[base + j] for j in range(nt))[::-1])
    return verts, faces, fuv, dict(s=s, top=top, bot=bot, wid=wid, zc=zc)


def smooth_closed(pts, sub=6, keep_tips=True):
    """Closed Catmull-Rom resampling of a fin outline (rounded, natural edges)."""
    P = np.asarray(pts, float); n = len(P); out = []
    for i in range(n):
        p0, p1, p2, p3 = P[(i - 1) % n], P[i], P[(i + 1) % n], P[(i + 2) % n]
        for k in range(sub):
            t = k / sub
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return np.array(out)


def build_median(sp, pts, thick=0.004):
    L = sp["L"]
    P = np.array([(-a * L, b * L) for a, b in smooth_closed(pts)])
    n = len(P); verts = []
    for side in (-1, 1):
        for x, z in P: verts.append((x, side * thick * L * 0.5, z))
    f1 = tuple(range(n)); f2 = tuple(n + k for k in range(n))[::-1]
    side_faces = [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)]
    tone = "dark"
    return np.array(verts), [f1, f2] + side_faces, tone


def build_paired(sp, prof, name, root_s, root_z, dihedral, outline):
    """Two fins (left/right). dihedral 0 = horizontal plane (flukes); 0.5 ~ swept down-out."""
    L = sp["L"]
    w_root = pchip(sp["body"]["s"], sp["body"]["wid"], root_s) * L * 0.8
    zc = pchip(sp["body"]["s"], sp["body"]["zc"], root_s) * L
    out = []
    for side in (-1, 1):
        if name == "fluke":
            span = np.array([0, side * 1.0, 0.0]); root = np.array([-root_s * L, 0.0, zc + root_z * L])
        else:
            span = np.array([0, side * math.cos(dihedral * math.pi / 2), -math.sin(dihedral * math.pi / 2)])
            root = np.array([-root_s * L, side * w_root, zc + root_z * L])
        chord = np.array([-1.0, 0, 0])
        V = [root + a * L * chord + b * L * span for a, b in smooth_closed(outline)]
        out.append(np.array(V))
    return out


def make_object(name, sp):
    verts, faces, fuv, prof = build_body(sp)
    all_v = [verts]; all_f = list(faces); all_uv = list(fuv); nv = len(verts)
    fin_tags = np.zeros(len(verts))       # 0 body, 1 median fin, 2 paired fin
    light_fins = {"humpback": ("flipper",), "orca": ()}
    for nm, pts in sp["median"]:
        v, f, tone = build_median(sp, pts)
        all_v.append(v); all_f += [tuple(nv + k for k in ff) for ff in f]
        all_uv += [tuple(np.array(FIN_UV["dark"]) for _ in ff) for ff in f]
        fin_tags = np.concatenate([fin_tags, np.ones(len(v))]); nv += len(v)
    for nm, rs, rz, dih, outline in sp["paired"]:
        for V in build_paired(sp, prof, nm, rs, rz, dih, outline):
            n = len(V); f = [tuple(range(n)), tuple(range(n))[::-1]]
            all_v.append(V); all_f += [tuple(nv + k for k in ff) for ff in f]
            tone = "light" if nm in light_fins.get(sp["tex"], ()) else ("mid" if nm == "fluke" and sp["tex"] == "humpback" else "dark")
            all_uv += [tuple(np.array(FIN_UV[tone]) for _ in ff) for ff in f]
            fin_tags = np.concatenate([fin_tags, np.full(n, 2.0)]); nv += n
    V = np.concatenate(all_v)
    me = bpy.data.meshes.new(name)
    me.from_pydata(V.tolist(), [], [list(f) for f in all_f])
    me.update()
    uvl = me.uv_layers.new(name="UVMap")
    loop_uv = []
    for f in all_uv:
        for q in f: loop_uv += [float(q[0]), float(q[1])]
    uvl.data.foreach_set("uv", loop_uv)
    for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob, V, fin_tags


def diver_object():
    """Scuba diver, 1.8 m tall, horizontal trim, facing +x; fins add ~0.6 m. Parts are ellipsoids.
    Returns object, rest verts, part index per vertex and part pivots (for the flutter kick)."""
    parts = []  # (center, radii, rot_y_deg, tone, group)
    def E(c, r, ry=0.0, tone="dark", g="body"): parts.append((np.array(c, float), np.array(r, float), ry, tone, g))
    E((-0.06, 0, 0.05), (0.12, 0.095, 0.115), -15)            # head (hood)
    E((0.0, 0, 0.05), (0.06, 0.07, 0.04), -15, "light")      # mask glass (slightly proud of the hood)
    E((-0.42, 0, 0.0), (0.32, 0.18, 0.15), 3)                 # torso + BCD
    E((-0.45, 0, 0.15), (0.30, 0.085, 0.085), 3, "mid")       # tank on back
    E((-0.15, 0, 0.17), (0.04, 0.04, 0.045), 0, "mid")        # valve
    E((-0.70, 0, -0.01), (0.15, 0.17, 0.13), 0)               # hips
    for side in (-1, 1):
        E((-0.22, side * 0.19, -0.10), (0.15, 0.055, 0.055), 40)  # upper arm (down-forward)
        E((-0.12, side * 0.13, -0.21), (0.16, 0.045, 0.045), -10) # forearm, hands folded under chest
        E((-0.98, side * 0.11, 0.0), (0.23, 0.08, 0.08), 0, "dark", f"thigh{side}")
        E((-1.38, side * 0.11, 0.0), (0.21, 0.06, 0.06), 0, "dark", f"shin{side}")
        E((-1.80, side * 0.11, 0.0), (0.30, 0.10, 0.012), 0, "dark", f"fin{side}")
    V, F, UVs, G = [], [], [], []
    nu, nvv = 18, 12
    for c, r, ry, tone, g in parts:
        base = len(V)
        for i in range(nvv + 1):
            ph = math.pi * i / nvv
            for j in range(nu):
                th = 2 * math.pi * j / nu
                p = np.array([math.sin(ph) * math.cos(th) * r[0], math.sin(ph) * math.sin(th) * r[1], math.cos(ph) * r[2]])
                a = math.radians(ry); R = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
                V.append(R @ p + c); G.append(g)
        for i in range(nvv):
            for j in range(nu):
                a = base + i * nu + j; b = base + i * nu + (j + 1) % nu; cc = base + (i + 1) * nu + (j + 1) % nu; d = base + (i + 1) * nu + j
                F.append((a, b, cc, d)); UVs.append(tuple(np.array(FIN_UV[tone]) for _ in range(4)))
    V = np.array(V)
    me = bpy.data.meshes.new("diver"); me.from_pydata(V.tolist(), [], F); me.update()
    uvl = me.uv_layers.new(name="UVMap")
    flat = []
    for f in UVs:
        for q in f: flat += [float(q[0]), float(q[1])]
    uvl.data.foreach_set("uv", flat)
    for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new("diver", me); bpy.context.scene.collection.objects.link(ob)
    return ob, V, np.array(G)


def diver_texture():
    nu, nv = 64, 16
    img = np.zeros((nv, nu, 3)) + np.array([.05, .055, .065])
    img[:, 16:32] = (.55, .65, .70)     # "light": mask glass glint
    img[:, 32:48] = (.30, .32, .34)     # "mid": tank
    img[:, 0:16] = (.05, .055, .065)
    return img


# ----------------------------------------------------------------------------- material + scene
def material(name, tex_np):
    nvv, nu = tex_np.shape[:2]
    # write the numpy texture to disk (16-bit PNG) and load it - generated in-memory images render black in bpy-module Cycles
    tdir = os.path.join(SCR, "sprite_tex"); os.makedirs(tdir, exist_ok=True)
    fn = os.path.join(tdir, name + ".png")
    im0 = bpy.data.images.new(name + "_tmp", nu, nvv, alpha=False)
    px = np.concatenate([tex_np[::-1], np.ones((nvv, nu, 1))], -1).astype(np.float32)   # bpy rows are bottom-up
    im0.pixels.foreach_set(px.ravel())
    im0.filepath_raw = fn; im0.file_format = "PNG"; im0.save()
    bpy.data.images.remove(im0)
    im = bpy.data.images.load(fn)
    im.colorspace_settings.name = "Non-Color"   # emission colour used linearly as designed
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; Lk = nt.links
    for n in list(N): N.remove(n)
    out = N.new("ShaderNodeOutputMaterial")
    em = N.new("ShaderNodeEmission")
    tx = N.new("ShaderNodeTexImage"); tx.image = im; tx.interpolation = "Linear"; tx.extension = "EXTEND"
    uvn = N.new("ShaderNodeUVMap"); uvn.uv_map = "UVMap"
    geo = N.new("ShaderNodeNewGeometry")
    dot = N.new("ShaderNodeVectorMath"); dot.operation = "DOT_PRODUCT"; dot.inputs[1].default_value = LIGHT.tolist()
    mx = N.new("ShaderNodeMath"); mx.operation = "MAXIMUM"; mx.inputs[1].default_value = 0.0
    # belly fill: light scattered up from below is weak; ambient keeps silhouettes readable
    sep = N.new("ShaderNodeSeparateXYZ")
    lw = N.new("ShaderNodeLayerWeight"); lw.inputs[0].default_value = 0.35
    shade = N.new("ShaderNodeMath"); shade.operation = "MULTIPLY_ADD"; shade.inputs[1].default_value = 0.85; shade.inputs[2].default_value = 0.05
    up = N.new("ShaderNodeMath"); up.operation = "MULTIPLY_ADD"; up.inputs[1].default_value = 0.10; up.inputs[2].default_value = 0.0
    tot = N.new("ShaderNodeMath"); tot.operation = "ADD"
    col = N.new("ShaderNodeVectorMath"); col.operation = "SCALE"
    rimp = N.new("ShaderNodeMath"); rimp.operation = "POWER"; rimp.inputs[1].default_value = 2.5
    rimz = N.new("ShaderNodeMath"); rimz.operation = "MULTIPLY_ADD"; rimz.inputs[1].default_value = 0.5; rimz.inputs[2].default_value = 0.5
    rimm = N.new("ShaderNodeMath"); rimm.operation = "MULTIPLY"
    rimc = N.new("ShaderNodeVectorMath"); rimc.operation = "SCALE"; rimc.inputs[0].default_value = (0.20, 0.42, 0.55)
    add = N.new("ShaderNodeVectorMath"); add.operation = "ADD"
    Lk.new(uvn.outputs[0], tx.inputs[0])
    Lk.new(geo.outputs["Normal"], dot.inputs[0]); Lk.new(dot.outputs["Value"], mx.inputs[0])
    Lk.new(mx.outputs[0], shade.inputs[0])
    Lk.new(geo.outputs["Normal"], sep.inputs[0]); Lk.new(sep.outputs[2], up.inputs[0])
    Lk.new(shade.outputs[0], tot.inputs[0]); Lk.new(up.outputs[0], tot.inputs[1])
    Lk.new(tx.outputs["Color"], col.inputs[0]); Lk.new(tot.outputs[0], col.inputs["Scale"])
    Lk.new(lw.outputs["Facing"], rimp.inputs[0]); Lk.new(sep.outputs[2], rimz.inputs[0])
    Lk.new(rimp.outputs[0], rimm.inputs[0]); Lk.new(rimz.outputs[0], rimm.inputs[1])
    Lk.new(rimm.outputs[0], rimc.inputs["Scale"])
    Lk.new(col.outputs[0], add.inputs[0]); Lk.new(rimc.outputs[0], add.inputs[1])
    Lk.new(add.outputs[0], em.inputs["Color"]); em.inputs["Strength"].default_value = 1.0
    Lk.new(em.outputs[0], out.inputs["Surface"])
    return m


def setup_scene(res_x, res_y, ortho, cam_xyz, samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"
    sc.cycles.samples = samples; sc.cycles.use_denoising = False; sc.cycles.use_adaptive_sampling = False
    sc.cycles.max_bounces = 0; sc.cycles.diffuse_bounces = 0; sc.cycles.glossy_bounces = 0; sc.cycles.transmission_bounces = 0
    sc.cycles.pixel_filter_type = "BLACKMAN_HARRIS"; sc.cycles.filter_width = 1.5
    sc.render.film_transparent = True
    sc.render.resolution_x = res_x; sc.render.resolution_y = res_y; sc.render.resolution_percentage = 100
    sc.render.threads_mode = "FIXED"; sc.render.threads = 2
    sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
    sc.render.image_settings.media_type = "IMAGE"; sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"; sc.render.image_settings.color_depth = "8"
    sc.world = bpy.data.worlds.new("w") if sc.world is None else sc.world
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes.get("Background")
    if bg: bg.inputs[1].default_value = 0.0
    cd = bpy.data.cameras.new("cam"); cd.type = "ORTHO"; cd.ortho_scale = ortho
    cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam); sc.camera = cam
    cam.location = cam_xyz
    cam.rotation_euler = (math.radians(90 + TILT), 0, 0)
    return sc, cam


def clear():
    for ob in list(bpy.data.objects): bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes): bpy.data.meshes.remove(me)
    for m in list(bpy.data.materials): bpy.data.materials.remove(m)
    for im in list(bpy.data.images): bpy.data.images.remove(im)
    for c in list(bpy.data.cameras): bpy.data.cameras.remove(c)


# ----------------------------------------------------------------------------- per-frame deformation
def deform(V, sp, phase, tags):
    L = sp["L"]; X = V[:, 0]; s = np.clip(-X / L, 0, 1.2)
    out = V.copy()
    w = 2 * np.pi * (phase - s / sp["lam"])
    if sp["kind"] == "shark":
        env = (0.12 + 0.88 * smoothstep(0.15, 1.0, s) ** 1.6)
        out[:, 1] += sp["lat"] * L * env * np.sin(w)
        out[:, 2] += 0.004 * L * np.sin(2 * np.pi * phase * 2)      # tiny heave
        # pectorals flex slightly
        out[:, 2] += np.where(tags == 2, 0.004 * L * np.sin(2 * np.pi * phase), 0)
    else:
        env = (0.10 + 0.90 * smoothstep(0.25, 1.0, s) ** 1.8)
        out[:, 2] += sp["vert"] * L * env * np.sin(w)
        out[:, 2] += 0.006 * L * np.sin(2 * np.pi * phase + 1.0)
        out[:, 1] += 0.006 * L * env * np.sin(w * 0.5)
    return out


def deform_diver(V, G, phase):
    out = V.copy()
    for side in (-1, 1):
        ph = 2 * np.pi * phase + (0 if side > 0 else np.pi)
        a_hip = math.radians(14) * math.sin(ph)
        a_knee = math.radians(10) * math.sin(ph - 0.9) + math.radians(8)
        hip = np.array([-0.75, 0, 0.0])
        knee0 = np.array([-1.19, 0, 0.0])
        def rot(p, piv, a):
            q = p - piv; c, s_ = math.cos(a), math.sin(a)
            return np.stack([q[:, 0] * c - q[:, 2] * s_, q[:, 1], q[:, 0] * s_ + q[:, 2] * c], 1) + piv
        for g in (f"thigh{side}", f"shin{side}", f"fin{side}"):
            m = G == g
            if not m.any(): continue
            P = rot(out[m], hip, a_hip)
            if g != f"thigh{side}":
                kn = rot(knee0[None, :], hip, a_hip)[0]
                P = rot(P, kn, a_knee)
                if g == f"fin{side}":
                    ank = rot(rot(np.array([[-1.58, 0, 0.0]]), hip, a_hip), kn, a_knee)[0]
                    P = rot(P, ank, math.radians(12) * math.sin(ph - 1.8))
            out[m] = P
    out[:, 2] += 0.01 * math.sin(2 * np.pi * phase * 1)
    return out


# ----------------------------------------------------------------------------- main
def render_species(key):
    clear()
    if key == "diver":
        ob, V, G = diver_object(); L = 2.45; cycle = 2.0; frames = 48
        ob.data.materials.append(material("diver", diver_texture()))
        sp = None
    else:
        sp = SPECIES[key]; L = sp["L"]; cycle = sp["cycle"]; frames = sp.get("frames", int(round(cycle * 24)))
        ob, V, tags = make_object(key, sp)
        ob.data.materials.append(material(key, make_texture(sp["tex"])))
    # bounding box over the whole cycle (projected through the tilted camera) -> sprite size
    xs, zs = [], []
    c, s_ = math.cos(math.radians(TILT)), math.sin(math.radians(TILT))
    for k in range(8):
        P = deform_diver(V, G, k / 8) if sp is None else deform(V, sp, k / 8, tags)
        xs += [P[:, 0].min(), P[:, 0].max()]
        sv = P[:, 2] * c - P[:, 1] * s_          # screen-up coordinate for the tilted camera
        zs += [sv.min(), sv.max()]
    x0, x1 = min(xs), max(xs); z0, z1 = min(zs), max(zs)
    m = 0.03 * L
    x0 -= m; x1 += m; z0 -= m; z1 += m
    width_m = x1 - x0; height_m = z1 - z0
    res_x = {"diver": 900, "bull": 1100, "gw": 1500, "mega": 1900, "whaleshark": 1600, "orca": 1300, "humpback": 1700,
             "blue": 1900, "perucetus": 1400}[key]
    if TEST: res_x //= 2
    ppm = res_x / width_m
    res_y = int(math.ceil(height_m * ppm / 2) * 2)
    cx = (x0 + x1) / 2; cz = (z0 + z1) / 2
    # camera centre in world: screen-up axis u = (0, -s, c); place camera so the centre maps to (cx, cz)
    cam_pos = (cx, -50 * c + (-s_) * cz * 0 , 0)
    sc, cam = setup_scene(res_x, res_y, width_m, (0, 0, 0), 4 if TEST else (6 if key != "perucetus" else 8))
    view = np.array([0, c, s_])      # camera looks along +y tilted up
    upv = np.array([0, -s_, c])
    centre = np.array([cx, 0, 0]) + upv * cz
    cam.location = tuple(centre - 60 * view)
    d = os.path.join(OUTD, key); os.makedirs(d, exist_ok=True)
    meta = dict(key=key, L=L, ppm=ppm, res=[res_x, res_y], nose_px=[(0 - x0) * ppm, None], frames=frames, cycle=cycle,
                tilt=TILT, x0=x0, x1=x1, z0=z0, z1=z1,
                axis_py=(z1 - 0.0) * ppm)          # pixel row of the body axis (z=0) from the top
    json.dump(meta, open(os.path.join(d, "meta.json"), "w"), indent=1)
    me = ob.data
    nf = 2 if TEST else frames
    for f in range(nf):
        fn = os.path.join(d, f"f_{f:03d}.png")
        if os.path.exists(fn) and not TEST: continue
        ph = f / frames
        P = deform_diver(V, G, ph) if sp is None else deform(V, sp, ph, tags)
        me.vertices.foreach_set("co", P.astype(np.float32).ravel()); me.update()
        sc.render.filepath = fn
        bpy.ops.render.render(write_still=True)
        print(key, f, flush=True)


keys = ["diver"] + list(SPECIES) if WHICH == "all" else WHICH.split(",")
for k in keys:
    render_species(k)
print("DONE", keys)
