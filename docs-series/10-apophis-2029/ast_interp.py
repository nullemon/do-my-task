"""Fill the odd asteroid frames (rendered on even frames only from 90 on) by optical-flow interpolation between neighbours.
The tumble is slow and rigid (<= 2.5 px per frame), so a mid-frame warped from both neighbours is very close to a render.
Usage: python3 ast_interp.py            (fills every missing odd frame whose neighbours exist)
       python3 ast_interp.py test 41    (rebuilds frame 41 from 40 and 42 and prints the error against the real render)"""
import sys, os, time, math
from lib import *
D = SCR + "/spr/ast"


def load(i):
    a = cv2.imread(f"{D}/f_{i:04d}.png", cv2.IMREAD_UNCHANGED).astype(F32) / 255      # BGRA straight alpha
    if a.shape[0] < 1300:                                     # early frames are 1000 px tall: pad to the common canvas
        p = (1300 - a.shape[0]) // 2; a = np.pad(a, ((p, 1300 - a.shape[0] - p), (0, 0), (0, 0)))
    return a


def mid(a, b, u=0.5):
    """frame at fraction u between a and b: warp both along the optical flow, blend, then restore render-like grain"""
    pa = a[..., :3] * a[..., 3:4]; pb = b[..., :3] * b[..., 3:4]
    ga = (cv2.cvtColor(pa, cv2.COLOR_BGR2GRAY) * 255).clip(0, 255).astype(np.uint8); gb = (cv2.cvtColor(pb, cv2.COLOR_BGR2GRAY) * 255).clip(0, 255).astype(np.uint8)
    f = cv2.calcOpticalFlowFarneback(ga, gb, None, 0.5, 6, 41, 6, 7, 1.5, 0)
    f = cv2.GaussianBlur(f, (0, 0), 7)
    h, w = ga.shape; xx, yy = np.meshgrid(np.arange(w, dtype=F32), np.arange(h, dtype=F32))
    A = np.dstack([pa, a[..., 3]]); B = np.dstack([pb, b[..., 3]])
    wa = cv2.remap(A, xx - u * f[..., 0], yy - u * f[..., 1], cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT)
    wb = cv2.remap(B, xx + (1 - u) * f[..., 0], yy + (1 - u) * f[..., 1], cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT)
    m = np.clip((1 - u) * wa + u * wb, 0, 1)
    al = m[..., 3:4]; rgb = np.where(al > 1e-4, m[..., :3] / np.maximum(al, 1e-4), 0)
    # blending two frames averages away the path-tracing noise: put matching grain back so the texture does not pulse
    lum = rgb.mean(-1, keepdims=True); k = 2 * math.sqrt(u * (1 - u))
    rgb = rgb + np.random.default_rng().standard_normal(rgb.shape[:2] + (1,)).astype(F32) * (0.028 * np.sqrt(np.clip(lum, 0, 1)) + 0.003) * k * (al > 0.5)
    return np.dstack([np.clip(rgb, 0, 1), al])


if len(sys.argv) > 1 and sys.argv[1] == "test":
    k0, k1 = int(sys.argv[2]), int(sys.argv[3]); A, B = load(k0), load(k1)
    for i in range(k0 + 1, k1):
        m = mid(A, B, (i - k0) / (k1 - k0)); r = load(i)
        pm = m[..., :3] * m[..., 3:4]; pr = r[..., :3] * r[..., 3:4]
        bl = lambda z: cv2.GaussianBlur(z, (0, 0), 2.0)
        print(i, "RMS err:", round(float(np.sqrt(((pm - pr) ** 2).mean())) * 255, 2), " structural (blurred) err:", round(float(np.sqrt(((bl(pm) - bl(pr)) ** 2).mean())) * 255, 2),
              " vs neighbour key:", round(float(np.sqrt(((bl(A[..., :3] * A[..., 3:4]) - bl(pr)) ** 2).mean())) * 255, 2))
        cv2.imwrite(SCR + f"/chk/interp_{i}.png", (np.hstack([pm[250:650, 450:950], pr[250:650, 450:950]]) * 255).clip(0, 255).astype(np.uint8))
else:
    have = sorted(int(f[2:6]) for f in os.listdir(D) if f.startswith("f_") and f.endswith(".png") and "tmp" not in f and not os.path.exists(f"{D}/{f}.i"))
    have = [i for i in have if time.time() - os.path.getmtime(f"{D}/f_{i:04d}.png") > 45]
    n = 0
    for k0, k1 in zip(have, have[1:]):
        if k1 - k0 < 2 or k1 - k0 > 4: continue
        A, B = load(k0), load(k1)
        for i in range(k0 + 1, k1):
            fn = f"{D}/f_{i:04d}.png"
            if os.path.exists(fn): continue
            cv2.imwrite(fn + ".tmp.png", (mid(A, B, (i - k0) / (k1 - k0)) * 255 + 0.5).astype(np.uint8), [cv2.IMWRITE_PNG_COMPRESSION, 3]); os.replace(fn + ".tmp.png", fn); open(fn + ".i", "w").close(); n += 1
    print("interpolated", n)
