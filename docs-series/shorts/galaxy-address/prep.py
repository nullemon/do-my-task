"""Sky plates for "What If Earth Were Somewhere Else in the Galaxy?" -> SCR/plates.npz
All plates are in a LOCAL azimuthal-equidistant frame around a scene's centre direction: plate pixel (u, v) =
(P/2 + theta_deg * PPD * cos phi, P/2 + theta_deg * PPD * sin phi), theta = angle from the centre direction.
  mw    NASA/JPL-Caltech/R. Hurt face-on Milky Way (PIA10748, public domain), linear light, square 2048 px,
        DISK_LY across the image width (the renderer maps it physically: R = h tan(theta), h = 30,000 ly)
  neb   procedural star-forming region seen from inside (Carina-like): pink H-alpha clouds, teal O III cores around
        the young clusters, dark dust pillars with bright ionisation rims
  nebstars  young O/B stars (clustered) + field stars, as local (theta, phi) + V + Teff
  void  six tiny faint galaxy sprites for the Bootes Void
Usage: /home/user/ttsenv/bin/python prep.py"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import lib.core  # noqa: F401
import numpy as np, cv2
from PIL import Image
from lib.core import f32, srgb_to_lin, lum, fbm2, smooth

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B3-galaxy-address"
DL = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B3-common/dl"
P = 2048
PPD = P / 2 / 110.0                       # plate px per degree (covers theta <= 110 deg)
MW_N = 2048


def mw_image():
    im = Image.open(os.path.join(DL, "PIA10748.jpg")).convert("RGB")
    im = im.resize((MW_N, MW_N), Image.LANCZOS)
    a = srgb_to_lin(np.asarray(im, f32) / 255.0)
    a = np.maximum(a - np.percentile(a.reshape(-1, 3), 8, axis=0), 0)       # black level (the image corners)
    y = lum(a)[..., None]; a = np.maximum(y + (a - y) * 1.35, 0)             # a little more colour
    yy, xx = np.mgrid[0:MW_N, 0:MW_N].astype(f32); r = np.hypot(xx - MW_N / 2, yy - MW_N / 2) / (MW_N / 2)
    a *= smooth(1.0, 0.92, r)[..., None]
    return a.astype(np.float16)


def nebula():
    rng = np.random.default_rng(7)
    yy, xx = np.mgrid[0:P, 0:P].astype(f32)
    dx, dy = (xx - P / 2) / PPD, (yy - P / 2) / PPD                           # degrees from the centre direction
    th = np.hypot(dx, dy)
    def N(seed, beta, n=512): return cv2.resize(fbm2((n, n), seed, beta), (P, P), interpolation=cv2.INTER_CUBIC)
    # young clusters (deg offsets): the light sources of the region
    CL = [(-8.0, -6.0, 1.0), (14.0, 4.0, 0.8), (-24.0, 18.0, 0.55), (30.0, -22.0, 0.45), (2.0, 30.0, 0.4)]
    near = np.zeros_like(th)
    for cx, cy, w in CL:
        near += w * np.exp(-np.hypot(dx - cx, dy - cy) / 18.0)
    # domain-warped low-frequency density -> billowing clouds with filaments
    w1, w2 = N(11, 3.4, 256) * 40, N(12, 3.4, 256) * 40
    mx = ((xx + w1) % P).astype(f32); my = ((yy + w2) % P).astype(f32)
    base = cv2.remap(N(13, 3.0, 512), mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    fil = cv2.remap(N(14, 2.6, 1024), mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    ridge = cv2.GaussianBlur((1 - np.abs(fil)) ** 4, (0, 0), 1.5)
    dens = np.clip(0.55 + 0.5 * base, 0, 2)
    cloud = dens ** 2.0 * (0.45 + 1.0 * ridge) * (0.30 + 1.7 * near + 0.20 * np.exp(-th / 60))
    # dust: big dark lanes and pillars; their edges facing the clusters glow (ionisation fronts)
    dn = cv2.remap(N(15, 3.3, 512), mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    dust = smooth(0.25, 0.85, dn + 0.25 * fil) * (1 - 0.6 * smooth(0.9, 1.6, near))
    edge = cv2.GaussianBlur(np.clip(dust - cv2.GaussianBlur(dust, (0, 0), 10), 0, 1), (0, 0), 3)
    rimv = edge * (0.3 + 2.0 * near)
    trans = 1 - 0.93 * dust
    ha = np.array([1.0, 0.20, 0.50], f32); o3 = np.array([0.20, 0.85, 1.00], f32); rim = np.array([1.0, 0.72, 0.45], f32)
    k = np.clip((near - 0.45) * 1.2, 0, 0.8)[..., None]
    img = cloud[..., None] * (ha * (1 - k) + o3 * k)
    img = img * trans[..., None] + np.clip(rimv, 0, 1.2)[..., None] * rim * 1.6 * dens[..., None]
    img += (near ** 2 * 0.30)[..., None] * np.array([0.35, 0.55, 1.0], f32) * trans[..., None]
    img = cv2.GaussianBlur(img, (0, 0), 0.7) * 0.06
    # stars: clustered young O/B stars + field
    th_s, ph_s, V, T = [], [], [], []
    for cx, cy, w in CL:
        n = int(40 * w) + 6
        r = np.abs(rng.normal(0, 2.5 + 3 * w, n)); a = rng.uniform(0, 2 * np.pi, n)
        x = cx + r * np.cos(a); y = cy + r * np.sin(a)
        th_s.append(np.hypot(x, y)); ph_s.append(np.arctan2(y, x))
        V.append(rng.uniform(-3.5, 1.5, n)); T.append(rng.uniform(18000, 42000, n))
    n = 9000
    u = rng.uniform(0, 1, n); th_f = np.degrees(np.arccos(1 - u * (1 - math.cos(math.radians(110)))))
    th_s.append(th_f); ph_s.append(rng.uniform(0, 2 * np.pi, n))
    V.append(np.clip(1.0 + rng.exponential(1.0, n) * 1.7, -1, 7.0)); T.append(np.where(rng.uniform(0, 1, n) < 0.65, rng.uniform(9000, 30000, n), rng.uniform(3500, 7000, n)))
    th_s.append([3.0]); ph_s.append([2.2]); V.append([-5.0]); T.append([25000.0])            # one very luminous star (Eta Car-like)
    stars = dict(th=np.concatenate(th_s).astype(f32), ph=np.concatenate(ph_s).astype(f32), V=np.concatenate(V).astype(f32),
                 T=np.concatenate(T).astype(f32))
    return img.astype(np.float16), stars


def void_sprites():
    mw = np.asarray(Image.open(os.path.join(DL, "PIA10748.jpg")).convert("RGB").resize((256, 256), Image.LANCZOS), f32) / 255.0
    mw = srgb_to_lin(mw)
    out = []
    S = 64
    yy, xx = np.mgrid[0:S, 0:S].astype(f32) - S / 2 + 0.5
    for k, (kind, inc, rot) in enumerate((("sp", 0.35, 20), ("el", 0.7, -30), ("sp", 0.8, 60), ("el", 0.5, 10), ("sp", 0.25, -50), ("el", 0.9, 0))):
        if kind == "sp":
            M = cv2.getRotationMatrix2D((128, 128), rot, 1.0); s = cv2.warpAffine(mw, M, (256, 256))
            s = cv2.resize(s, (S, int(S * inc) | 1), interpolation=cv2.INTER_AREA)
            o = np.zeros((S, S, 3), f32); y0 = (S - s.shape[0]) // 2; o[y0:y0 + s.shape[0]] = s
        else:
            c, sn = math.cos(math.radians(rot)), math.sin(math.radians(rot))
            u = (xx * c + yy * sn) / 18; v = (-xx * sn + yy * c) / (18 * inc)
            r = np.sqrt(u * u + v * v)
            o = (np.exp(-r * 3.2) * 1.6)[..., None] * np.array([1.0, 0.82, 0.62], f32)
        out.append(o)
    return np.stack(out).astype(f32)


if __name__ == "__main__":
    os.makedirs(SCR, exist_ok=True)
    mw = mw_image(); print("mw", mw.shape)
    neb, st = nebula(); print("neb", neb.shape, float(neb.astype(f32).max()), "stars", len(st["V"]))
    vs = void_sprites()
    np.savez(os.path.join(SCR, "plates.npz"), mw=mw, neb=neb, void=vs, **{f"ns_{k}": v for k, v in st.items()})
    # previews
    def pv(a, p, k=1.0):
        a = np.asarray(a, f32); a = 1 - np.exp(-a * k); a = np.clip(a, 0, 1) ** (1 / 2.2)
        Image.fromarray((a * 255).astype(np.uint8)).resize((512, 512)).save(p)
    pv(mw, os.path.join(SCR, "pv_mw.jpg"), 2.0); pv(neb, os.path.join(SCR, "pv_neb.jpg"), 3.0)
    print("ok")
