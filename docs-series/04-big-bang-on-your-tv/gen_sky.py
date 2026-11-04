"""Equirect blue-hour sky with stars for the Holmdel horn shots (python3 + numpy + PIL)."""
import numpy as np
from PIL import Image
OUT = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/04-big-bang-on-your-tv/tex/horn_sky.png"
W, H = 6144, 3072
rng = np.random.default_rng(4)
v = (np.arange(H) + 0.5) / H              # 0 top .. 1 bottom
lat = (0.5 - v) * np.pi                   # +pi/2 zenith
u = (np.arange(W) + 0.5) / W
lon = (u - 0.5) * 2 * np.pi
LAT, LON = np.meshgrid(lat, lon, indexing="ij")
alt = np.clip(LAT, 0, None)
# blue hour gradient: deep navy zenith -> teal-blue -> warm band at horizon toward az=+X (lon=0)
zen = np.array([0.006, 0.010, 0.030]); mid = np.array([0.020, 0.040, 0.090]); hor = np.array([0.10, 0.07, 0.07])
t = np.clip(alt / (np.pi / 2), 0, 1)[..., None]
sky = mid * (1 - t) ** 3 + zen * (1 - (1 - t) ** 3)
warm = np.exp(-alt / 0.10)[..., None] * (0.45 + 0.55 * np.cos(LON)[..., None].clip(0, 1) ** 2)
sky = sky + warm * hor
# stars (more visible higher up)
n = 9000
sy = rng.integers(0, H // 2, n); sx = rng.integers(0, W, n)
mag = rng.random(n) ** 6
vis = np.clip((0.5 - (sy + 0.5) / H) * 2 / 0.25, 0, 1)
img = sky.copy()
for dy in (0, 1):
    for dx in (0, 1):
        w = (0.6 if dx or dy else 1.0)
        img[np.clip(sy + dy, 0, H - 1), (sx + dx) % W] += (mag * vis * w * 0.9)[:, None] * np.array([0.9, 0.95, 1.0])
# below horizon: dark ground haze (ground plane covers it anyway)
img[LAT < 0] = hor * 0.25
img = np.clip(img, 0, 1) ** (1 / 2.2)
Image.fromarray((img * 255).astype(np.uint8)).save(OUT)
print("ok", OUT)
