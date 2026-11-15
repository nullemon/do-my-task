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


def main():
    os.makedirs(SCR, exist_ok=True); T0 = time.time()
    # ---------------- halo (2048 x 1024)
    v = dirs(2048, 1024).astype(np.float32)
    J = nfw_column(v)
    print("NFW column GC / anticentre / pole:", round(J[512, 1024] / J[512, 0], 1), round(J[0, 0] / J[512, 0], 2), f"{time.time()-T0:.0f}s", flush=True)
    halo = (J / J[512, 0]) ** 0.55                                                 # perceptual compression; everywhere > 0
    w1 = waves(v, 70, 1.5, 9.0, 11); w2 = waves(v, 90, 6.0, 26.0, 12)
    wisp = np.clip(1.0 + 0.30 * w1 + 0.16 * w2, 0.35, 2.0)
    halo = (halo * wisp).astype(np.float32)
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
    # ---------------- web (4096 x 2048), in row chunks (memory)
    def seeds(nseed, seed):
        rr = np.random.default_rng(seed); p = rr.normal(size=(nseed, 3)); return cKDTree(p / np.linalg.norm(p, axis=1, keepdims=True))
    T1, T2 = seeds(70, 31), seeds(300, 32)
    def cellnet(v, tree, seed, warp):
        vw = v + warp * np.stack([waves(v, 40, 2.0, 10.0, seed + j) for j in range(3)], -1)
        vw /= np.linalg.norm(vw, axis=-1, keepdims=True)
        dd, _ = tree.query(vw.reshape(-1, 3), k=3, workers=2)
        return (dd[:, 1] - dd[:, 0]).reshape(v.shape[:-1]), (dd[:, 2] - dd[:, 0]).reshape(v.shape[:-1])
    web = np.zeros((2048, 4096), np.float32)
    vall = dirs(4096, 2048)
    for r0 in range(0, 2048, 256):
        v = vall[r0:r0 + 256]
        e1, n1 = cellnet(v, T1, 31, 0.10)
        e2, n2 = cellnet(v, T2, 32, 0.05)
        var = np.clip(0.30 + 0.75 * waves(v, 50, 2.0, 8.0, 41), 0.0, 1.8) ** 1.5         # threads brighten / fade along their length
        var2 = np.clip(-0.2 + 0.8 * waves(v, 60, 3.0, 14.0, 42), 0.0, 1.2) ** 2          # most of the fine mesh is absent
        w = (np.exp(-(e1 / 0.011) ** 2) * 1.0 + np.exp(-(e1 / 0.040) ** 2) * 0.35) * var
        w += (np.exp(-(e2 / 0.007) ** 2) * 0.45 + np.exp(-(e2 / 0.020) ** 2) * 0.12) * var2
        w += np.exp(-(n1 / 0.030) ** 2) * 1.4 * var + np.exp(-(n2 / 0.016) ** 2) * 0.30 * var2      # knots where threads meet
        web[r0:r0 + 256] = w
    del vall
    web = cv2.GaussianBlur(web, (0, 0), 0.8)
    print("web", f"{time.time()-T0:.0f}s", flush=True)
    np.savez(os.path.join(SCR, "dm.npz"), halo=halo.astype(np.float16), clumps=clumps.astype(np.float16), web=web.astype(np.float16))
    print("saved", f"{time.time()-T0:.0f}s")


if __name__ == "__main__":
    main()
