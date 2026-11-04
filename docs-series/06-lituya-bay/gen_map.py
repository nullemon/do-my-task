"""Top-down shaded map of the stylised bay (numpy), north up.  Writes a 'top' pseudo-plate the compositor
treats like a Blender plate: top_forest.npy / top_strip.npy (linear RGB), top_data.npy (world xyz + alpha), top_cam.json."""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import world as Wd
from world import sst

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/06-lituya-bay"
PL = os.path.join(SCR, "plates"); os.makedirs(PL, exist_ok=True)
RW, RH = 2880, 1620
OSCALE = 21500.0                      # metres across the plate
C = np.array([-700.0, 6300.0])        # map centre (m)
# map +y points to real azimuth ~45 deg -> real north on screen-up is map direction (-0.707, 0.707)
XC = np.array([math.sqrt(0.5), math.sqrt(0.5), 0.0])     # screen right = real east
YC = np.array([-math.sqrt(0.5), math.sqrt(0.5), 0.0])    # screen up = real north
ZC = np.array([0.0, 0.0, 1.0])
M = np.eye(4); M[:3, 0] = XC; M[:3, 1] = YC; M[:3, 2] = ZC; M[:3, 3] = [C[0], C[1], 30000.0]

s = OSCALE / RW
u = (np.arange(RW) + 0.5 - RW / 2) * s
v = (RH / 2 - (np.arange(RH) + 0.5)) * s
U, V = np.meshgrid(u, v)
X = C[0] + U * XC[0] + V * YC[0]
Y = C[1] + U * XC[1] + V * YC[1]
xk = (X / 1000).astype(np.float32); yk = (Y / 1000).astype(np.float32)
F = Wd.fields(xk, yk)
h = F["h"]; dw = F["dw"]; gm = F["gm"]
hs = h.copy()
for _ in range(3):
    hs = (np.roll(hs, 1, 0) + np.roll(hs, -1, 0) + np.roll(hs, 1, 1) + np.roll(hs, -1, 1) + hs) / 5
gy, gx = np.gradient(hs, s)          # along rows (screen down) and columns (screen right)
# light from the real north-west (screen upper-left)
nrm = np.stack([-gx, gy, np.ones_like(h)], -1); nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
L = np.array([-0.55, 0.55, 0.63]); L /= np.linalg.norm(L)
shade = np.clip(nrm @ L, 0, 1)
shade = 0.35 + 0.9 * shade
land = np.array([0.050, 0.062, 0.052])[None, None] * (1 + 0.5 * sst(200, 1400, h))[..., None]
rock = np.array([0.08, 0.078, 0.075])
land = land * (1 - sst(900, 1600, h)[..., None]) + rock * sst(900, 1600, h)[..., None]
snow = sst(1500, 2000, h)[..., None]
col = land * (1 - snow) + np.array([0.55, 0.58, 0.62]) * snow
col = col * (1 - gm[..., None]) + np.array([0.42, 0.48, 0.55]) * gm[..., None]
col = col * shade[..., None]
depth = np.clip(-h / 200, 0, 1)
water = np.array([0.020, 0.040, 0.070])[None, None] * (1 - 0.45 * depth[..., None])
wm = (dw < 0)[..., None]
col = np.where(wm, water, col)
# soft coastline glow
edge = np.exp(-(np.abs(dw) / 0.03) ** 2)[..., None] * 0.035
col = col + edge * np.array([0.6, 0.8, 1.0])
forest = col.astype(np.float32)
R = Wd.runup(xk, yk)
wet = ((h < R) & (dw >= 0) & (dw < Wd.wet_limit(xk, yk)) & (gm < 0.5)).astype(np.float32)
strip = forest * (1 - wet[..., None]) + (np.array([0.20, 0.11, 0.06]) * shade[..., None] * 1.2) * wet[..., None]
np.save(os.path.join(PL, "top_forest.npy"), forest.astype(np.float16))
np.save(os.path.join(PL, "top_strip.npy"), strip.astype(np.float16))
data = np.stack([X, Y, np.where(dw < 0, -5.0, h), np.ones_like(X)], -1).astype(np.float32)
np.save(os.path.join(PL, "top_data.npy"), data)
json.dump(dict(cam="top", matrix_world=M.tolist(), lens=50.0, sensor_width=36.0, ortho=True, ortho_scale=OSCALE,
               res=[RW, RH]), open(os.path.join(PL, "top_cam.json"), "w"), indent=1)
print("map plate written", forest.max())
