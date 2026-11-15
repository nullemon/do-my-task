"""Dark-matter sky canvases for "What If You Could See Dark Matter?" -> SCR/dm.npz
All canvases are FULL-SKY equirectangular maps in GALACTIC coordinates (x: l = 0 at the centre column, increasing to
the right like mwsky.py; y: b = +90 at the top), so they turn with the real sky exactly like the Milky Way band.
  halo    line-of-sight column of an NFW halo (r_s = 20 kpc, Sun at R0 = 8.2 kpc, out to 250 kpc), slightly flattened
          (q = 0.9), times soft volumetric wisps (smooth 3-D plane-wave noise on the sphere: no seams, no brush strokes)
  clumps  ~420 subhalos: projected NFW-like cores, power-law angular sizes (a few big, many small), one big clump at the
          Sagittarius dwarf (l = 5.6, b = -14.2)
  web     cosmic-web filaments: domain-warped spherical Voronoi edges (F2 - F1) at two scales + bright knots where
          threads meet (F3 - F1 small)
Usage: /home/user/ttsenv/bin/python prep.py"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import lib.core  # noqa: F401
import numpy as np, cv2
from scipy.spatial import cKDTree

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B4-dark-matter-visible"
R0, RS, RMAX, Q = 8.2, 20.0, 250.0, 0.9


def dirs(W, H):
    """galactic unit vectors (x -> GC, y -> l = 90, z -> NGP) for every canvas pixel"""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64) + 0.5
    l = np.radians((xx - W / 2) * 360.0 / W); b = np.radians(90.0 - yy * 180.0 / H)
    return np.stack([np.cos(b) * np.cos(l), np.cos(b) * np.sin(l), np.sin(b)], -1)


def waves(v, n, kmin, kmax, seed):
    """smooth 3-D noise on the sphere: sum of random plane waves, amplitude ~ 1/k (fBm-like), unit variance"""
    r = np.random.default_rng(seed); out = np.zeros(v.shape[:-1], np.float32); var = 0.0
    for _ in range(n):
        k = r.normal(size=3); k /= np.linalg.norm(k); km = math.exp(r.uniform(math.log(kmin), math.log(kmax)))
        out += np.sin((v @ (k * km).astype(np.float32)) + np.float32(r.uniform(0, 6.283))) / np.float32(km); var += 0.5 / km ** 2
    return out / np.float32(math.sqrt(var))


def nfw_column(v):
    """integral of rho_NFW along the line of sight from the Sun (arbitrary units)"""
    s = np.concatenate([np.linspace(0.01, 30, 600), np.linspace(30.1, RMAX, 600)])
    ds = np.gradient(s)
    flat = v.reshape(-1, 3); out = np.zeros(len(flat))
    for i in range(0, len(flat), 20000):
        d = flat[i:i + 20000]
        x = -R0 + d[:, 0:1] * s; y = d[:, 1:2] * s; z = d[:, 2:3] * s / Q          # Sun at (-R0, 0, 0)... GC at origin
        r = np.sqrt(x * x + y * y + z * z) + 0.05
        u = r / RS; out[i:i + 20000] = (ds / (u * (1 + u) ** 2)).sum(1)
    return out.reshape(v.shape[:-1])


def unit(x): return x / np.linalg.norm(x, axis=-1, keepdims=True)


def build_web(W, H):
    """Cosmic-web look (Millennium / Illustris style): cluster knots (some grouped into superclusters) joined to their
    nearest neighbours by filaments that are thick and bright near the knots and taper in between, bent by a smooth
    domain warp, with short side branches tapering to nothing, a faint broad 'sheet' glow around each filament, empty
    voids between, a fibrous grain of tiny galaxies along the threads, and two depth layers (near: thicker, brighter)."""
    r = np.random.default_rng(55)
    v = dirs(W, H).astype(np.float32).reshape(-1, 3)
    wv = np.stack([waves(v, 40, 2.0, 9.0, 61 + j) for j in range(3)], -1)
    vw = unit(v + 0.045 * wv).astype(np.float32); del wv
    sc = unit(r.normal(size=(18, 3)))                                              # superclusters
    nodes = [unit(sc[r.integers(18)] + r.normal(size=3) * 0.22) for _ in range(80)] + list(unit(r.normal(size=(36, 3))))
    nodes = np.array(nodes); K = len(nodes)
    depth = r.uniform(0, 1, K)
    ang = np.arccos(np.clip(nodes @ nodes.T, -1, 1)); np.fill_diagonal(ang, 9)
    edges = set()
    for i in range(K):
        for j in np.argsort(ang[i])[: r.integers(2, 5)]:
            if ang[i, j] < math.radians(48): edges.add((min(i, j), max(i, j)))
    deg = np.zeros(K)
    for i, j in edges: deg[i] += 1; deg[j] += 1
    segs = []                                                                      # (a, b, width_a, width_b, bright, depth, free_end)
    for i, j in edges:
        dp = (depth[i] + depth[j]) / 2; w0 = math.radians(0.6 + 1.6 * dp) * r.uniform(0.7, 1.3)
        segs.append((nodes[i], nodes[j], w0, w0, (0.35 + 0.65 * dp) * r.uniform(0.6, 1.2), dp, False))
        for _ in range(r.integers(0, 2)):                                          # side branches
            s0 = r.uniform(0.25, 0.75); p0 = unit(nodes[i] * (1 - s0) + nodes[j] * s0)
            dirn = unit(np.cross(p0, nodes[j] - nodes[i]) * r.choice([-1, 1]) + (nodes[j] - nodes[i]) * r.uniform(-0.5, 0.5))
            L = math.radians(r.uniform(4, 10)); p1 = unit(p0 * math.cos(L) + dirn * math.sin(L))
            segs.append((p0, p1, w0 * 0.7, w0 * 0.25, (0.35 + 0.65 * dp) * 0.6, dp, True))
    FN = np.zeros(len(v), np.float32); FF = np.zeros(len(v), np.float32)
    for a, b, wa, wb, br, dp, free in segs:
        th_ab = math.acos(np.clip(a @ b, -1, 1)); mid = unit(a + b); n = unit(np.cross(a, b))
        idx = np.flatnonzero(vw @ mid.astype(np.float32) > math.cos(th_ab / 2 + 10 * max(wa, wb) + 0.02))
        x = vw[idx].astype(np.float64)
        pn = x @ n; perp = np.abs(np.arcsin(np.clip(pn, -1, 1)))
        vp = x - pn[:, None] * n[None]
        th = np.arctan2((np.cross(a, vp) @ n), vp @ a); s = th / th_ab
        da = np.arccos(np.clip(x @ a, -1, 1)); db = np.arccos(np.clip(x @ b, -1, 1))
        d = np.where((s >= 0) & (s <= 1), perp, np.minimum(da, db)); s = np.clip(s, 0, 1)
        if free: w = wa * (1 - s) + wb * s; bb = br * (1 - 0.8 * s)
        else:
            tap = 0.45 + 0.55 * np.abs(2 * s - 1) ** 1.6                           # thick near the knots, thin in between
            w = wa * tap; bb = br * (0.55 + 0.45 * tap)
        f = bb * (np.exp(-(d / w) ** 2) + 0.35 * np.exp(-(d / (2.5 * w)) ** 2) + 0.12 * np.exp(-(d / (8 * w)) ** 2))
        (FN if dp > 0.45 else FF)[idx] += f.astype(np.float32)
    for k in range(K):                                                             # cluster knots
        th = np.arccos(np.clip(vw @ nodes[k].astype(np.float32), -1, 1))
        sz = math.radians(0.5 + 0.35 * deg[k]) * (0.5 + 0.7 * depth[k])
        f = (0.6 + 0.25 * deg[k]) * (np.exp(-(th / sz) ** 2) * 1.6 + np.exp(-th / (3 * sz)) * 0.25) * (0.4 + 0.6 * depth[k])
        (FN if depth[k] > 0.45 else FF)[:] += np.where(th < 25 * sz, f, 0).astype(np.float32)
    fib = np.clip(0.70 + 0.45 * (1 - np.abs(np.tanh(waves(vw, 70, 25.0, 90.0, 71)))) ** 3 + 0.12 * waves(vw, 40, 40.0, 140.0, 72), 0.4, 1.6)
    FN *= fib; FF *= fib
    for F in (FN, FF):                                                             # granular galaxies along the threads
        p = np.clip(F, 0, None) ** 1.6; p = p / p.sum()
        pick = r.choice(len(F), 90000, p=p); np.add.at(F, pick, r.uniform(0.2, 1.0, len(pick)).astype(np.float32) * 0.5)
    FN = cv2.GaussianBlur(FN.reshape(H, W), (0, 0), 0.7); FF = cv2.GaussianBlur(FF.reshape(H, W), (0, 0), 0.7)
    return FN, FF


def main():
    os.makedirs(SCR, exist_ok=True); T0 = time.time()
    # ---------------- halo (2048 x 1024)
    v = dirs(2048, 1024).astype(np.float32)
    J = nfw_column(v)
    print("NFW column GC / anticentre / pole:", round(J[512, 1024] / J[512, 0], 1), round(J[0, 0] / J[512, 0], 2), f"{time.time()-T0:.0f}s", flush=True)
    Jn = (J / J[512, 0]).astype(np.float32)                                     # column relative to the anticentre (1 .. ~18)
    w1 = waves(v, 70, 1.5, 9.0, 11); w2 = waves(v, 90, 6.0, 26.0, 12); w3 = waves(v, 60, 3.0, 12.0, 13)
    wisp = np.clip(0.55 + 0.75 * (1 - np.abs(np.tanh(w1 * 0.8))) ** 2 + 0.22 * w2 + 0.15 * w3, 0.25, 2.0).astype(np.float32)   # ridged wisps
    # ---------------- clumps (2048 x 1024)
    r = np.random.default_rng(21); n = 420
    d = r.normal(size=(n, 3)); d /= np.linalg.norm(d, axis=1, keepdims=True)
    size = np.clip(0.35 * r.uniform(0, 1, n) ** (-0.75), 0.35, 9.0)             # core angle (deg), power law
    gain = r.uniform(0.6, 1.3, n) * (0.55 + 0.45 * np.clip(size / 3, 0, 1))
    sgr = np.array([math.cos(math.radians(-14.2)) * math.cos(math.radians(5.6)), math.cos(math.radians(-14.2)) * math.sin(math.radians(5.6)), math.sin(math.radians(-14.2))])
    d = np.vstack([d, sgr]); size = np.append(size, 6.5); gain = np.append(gain, 1.4)
    clumps = np.zeros((1024, 2048), np.float32)
    bdeg = 90.0 - (np.arange(1024) + 0.5) * 180.0 / 1024
    for k in range(len(d)):
        b0 = math.degrees(math.asin(d[k, 2])); ext = size[k] * 6 + 1
        rows = np.where(np.abs(bdeg - b0) < ext)[0]
        if not len(rows): continue
        sub = v[rows[0]:rows[-1] + 1]
        th = np.degrees(np.arccos(np.clip(sub @ d[k], -1, 1)))
        th = np.minimum(th, ext)
        prof = 1.0 / (1 + (th / size[k]) ** 2) * np.exp(-th / (size[k] * 2.2)) * (th < ext)
        clumps[rows[0]:rows[-1] + 1] += (prof * gain[k]).astype(np.float32)
    print("clumps", f"{time.time()-T0:.0f}s", flush=True)
    del v
    # ---------------- web (3072 x 1536): a graph of tapered, curved, branching filaments between cluster knots
    webN, webF = build_web(3072, 1536)
    print("web", f"{time.time()-T0:.0f}s", flush=True)
    np.savez(os.path.join(SCR, "dm.npz"), J=Jn.astype(np.float16), wisp=wisp.astype(np.float16), clumps=clumps.astype(np.float16), webN=webN.astype(np.float16), webF=webF.astype(np.float16))
    print("saved", f"{time.time()-T0:.0f}s")


if __name__ == "__main__":
    main()
