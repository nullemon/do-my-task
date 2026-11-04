"""Pre-baked numpy textures for 65 DAYS (run once with system python3: numpy + PIL).
stars_eq.png      4096x2048 equirect star field (for Blender world + compositor)
moon.png          2048x1024 procedural Moon albedo (maria + craters)
gran_a/b.npy      2048^2 periodic granulation tiles (float16, mean 1)
sunlow.npy        1024^2 low-frequency photosphere modulation on the visible disk (supergranulation, faculae, a few spots)
"""
import numpy as np, os
from PIL import Image
OUT = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/01-65-days/tex"
os.makedirs(OUT, exist_ok=True)
R = np.random.default_rng(65)

def fft_noise(n, m, kpeak=None, beta=None, width=0.35, seed=0):
    r = np.random.default_rng(seed)
    w = r.standard_normal((n, m)).astype(np.float32)
    F = np.fft.rfft2(w)
    ky = np.fft.fftfreq(n)[:, None] * n; kx = np.fft.rfftfreq(m)[None, :] * m
    k = np.sqrt(kx**2 + ky**2) + 1e-6
    if kpeak is not None:
        filt = np.exp(-(np.log(k / kpeak))**2 / (2 * width**2))
    else:
        filt = k ** (-beta / 2); filt[0, 0] = 0
    f = np.fft.irfft2(F * filt, s=(n, m)).astype(np.float32)
    return (f - f.mean()) / (f.std() + 1e-9)

def stars():
    W, Hh = 4096, 2048
    img = np.zeros((Hh, W), np.float32)
    n = 16000
    # uniform on sphere
    z = R.uniform(-1, 1, n); lon = R.uniform(0, 2*np.pi, n)
    lat = np.arcsin(z)
    x = (lon / (2*np.pi) * W); y = ((0.5 - lat/np.pi) * Hh)
    mag = R.power(0.18, n)            # many faint, few bright
    flux = 0.04 + 1.6 * (1 - mag)**6 + 0.12 * R.random(n)
    xi = np.clip(x.astype(int), 0, W-1); yi = np.clip(y.astype(int), 0, Hh-1)
    np.add.at(img, (yi, xi), flux)
    # slight soft bloom for bright stars
    from numpy.fft import rfft2, irfft2
    yy, xx = np.mgrid[-3:4, -3:4]; ker = np.exp(-(xx**2+yy**2)/1.2); ker /= ker.sum()
    big = np.zeros_like(img); big[:7, :7] = ker; big = np.roll(big, (-3, -3), (0, 1))
    soft = irfft2(rfft2(img) * rfft2(big), s=img.shape)
    img = 0.55*img + 0.9*soft
    col = np.stack([img*0.95, img*0.97, img*1.05], -1)
    # tint some stars
    a = np.clip(col, 0, 1) ** (1/2.2)
    Image.fromarray((a*255).astype(np.uint8)).save(f"{OUT}/stars_eq.png")

def moon():
    W, Hh = 2048, 1024
    base = 0.55 + 0.10 * fft_noise(Hh, W, beta=3.2, seed=3)
    maria = fft_noise(Hh, W, beta=4.2, seed=4)
    base -= 0.20 * np.clip(maria - 0.3, 0, None)
    lat = (0.5 - (np.arange(Hh) + 0.5) / Hh)[:, None] * np.pi
    yy, xx = np.mgrid[0:Hh, 0:W].astype(np.float32)
    for _ in range(700):
        cx, cy = R.uniform(0, W), R.uniform(0.05*Hh, 0.95*Hh)
        rr = R.pareto(1.6) * 4 + 3
        if rr > 80: continue
        sx = rr / max(0.15, np.cos((0.5 - cy/Hh)*np.pi))
        x0, x1 = int(max(0, cx - 2*sx)), int(min(W, cx + 2*sx)); y0, y1 = int(max(0, cy - 2*rr)), int(min(Hh, cy + 2*rr))
        dx = (xx[y0:y1, x0:x1] - cx) / sx; dy = (yy[y0:y1, x0:x1] - cy) / rr
        d = np.sqrt(dx*dx + dy*dy)
        base[y0:y1, x0:x1] += 0.06 * np.exp(-((d - 1)/0.15)**2) - 0.04 * (d < 0.9)
    a = np.clip(base, 0.05, 1)
    rgb = np.stack([a*1.0, a*0.98, a*0.94], -1)
    Image.fromarray((np.clip(rgb, 0, 1)**(1/2.2)*255).astype(np.uint8)).save(f"{OUT}/moon.png")

def granulation(seed, n=2048, cells=160):
    """Worley (cellular) granulation on a periodic tile: bright convective cells, dark intergranular lanes."""
    r = np.random.default_rng(seed)
    c = n / cells
    jit = r.uniform(0.1, 0.9, (cells, cells, 2)).astype(np.float32)
    bright = r.uniform(0.75, 1.25, (cells, cells)).astype(np.float32)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    wx = fft_noise(n, n, kpeak=cells/3.0, width=0.5, seed=seed+7) * c * 0.16
    wy = fft_noise(n, n, kpeak=cells/3.0, width=0.5, seed=seed+8) * c * 0.16
    px, py = (xx + wx) / c, (yy + wy) / c
    ix, iy = np.floor(px).astype(np.int32), np.floor(py).astype(np.int32)
    f1 = np.full((n, n), 9.0, np.float32); f2 = np.full((n, n), 9.0, np.float32); b1 = np.ones((n, n), np.float32)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            cx, cy = ix + dx, iy + dy
            mx, my = cx % cells, cy % cells
            fx = cx + jit[my, mx, 0]; fy = cy + jit[my, mx, 1]
            d = np.sqrt((px - fx)**2 + (py - fy)**2)
            closer = d < f1
            f2 = np.where(closer, f1, np.minimum(f2, d))
            b1 = np.where(closer, bright[my, mx], b1)
            f1 = np.where(closer, d, f1)
    edge = f2 - f1                        # 0 on the lanes
    lane = np.exp(-(edge / 0.13)**2)
    centre = np.exp(-(f1 / 0.55)**2)
    fine = fft_noise(n, n, kpeak=cells*2.5, width=0.5, seed=seed+9)
    g = b1 * (0.72 + 0.42*centre) * (1 - 0.62*lane) * (1 + 0.04*fine)
    g /= g.mean()
    np.save(f"{OUT}/gran_{'ab'[seed%2]}.npy", g.astype(np.float16))

def sunlow(n=1024):
    sup = fft_noise(n, n, kpeak=34, width=0.35, seed=21)    # supergranulation network (faint)
    m = 1.0 + 0.025*sup
    yy, xx = (np.mgrid[0:n, 0:n] + 0.5) / n * 2 - 1
    # a small sunspot group + faculae (kept modest)
    for (cx, cy, r) in [(0.28, -0.22, 0.020), (0.33, -0.20, 0.012), (0.25, -0.25, 0.008), (-0.42, 0.18, 0.015), (-0.38, 0.17, 0.007)]:
        d = np.sqrt((xx-cx)**2 + (yy-cy)**2) / r
        m *= 1 - 0.72*np.exp(-(d/0.55)**4) - 0.25*np.exp(-(d/1.15)**4)
        m += 0.05*np.exp(-((d-2.4)/1.4)**2)
    np.save(f"{OUT}/sunlow.npy", m.astype(np.float32))

if __name__ == "__main__":
    stars(); print("stars"); moon(); print("moon")
    granulation(0); granulation(1, cells=136); print("gran"); sunlow(); print("sunlow")
