"""Space shots for Shorts (linear HDR), ported from docs-series/08 lib.py:
 earth()     analytic orthographic Earth with real maps (NASA Blue Marble day, Black Marble night lights, cloud layer with
             cloud shadows, water mask glint, topology relief), Rayleigh limb, frost/ice cover, faint 'illustration' fill
 sun_disc()  photosphere with drifting granulation, wavelength-dependent limb darkening, faculae, sunspot map, chromosphere,
             arched prominences, streamer corona
 space_sky() static (no scintillation) star field + Milky Way from the StarSky plate
 lens_warp() point-mass lens applied to a rendered background (screen space): beta = theta - thetaE^2 theta/|theta|^2,
             plus an (enlarged) shadow disc
Textures: three-globe example/img + clouds (npm), threex.planets images (GitHub), see README.
"""
import math, os
import numpy as np, cv2
from PIL import Image
from .core import f32, smooth, fbm2, srgb_to_lin, COMMON

G = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/dl_globe/package/example"
TP = os.path.join(COMMON, "dl/threex.planets/images")


def norm(v): v = np.asarray(v, float); return v / np.linalg.norm(v)
def lin(x): return srgb_to_lin(x)

_tex = {}
def tex(name):
    if name in _tex: return _tex[name]
    def ld(p, mode="RGB"): return np.asarray(Image.open(p).convert(mode), f32) / 255
    if name == "day": t = lin(ld(G + "/img/earth-blue-marble.jpg"))
    elif name == "night": t = lin(ld(G + "/img/earth-night.jpg"))
    elif name == "water": t = cv2.resize(ld(G + "/img/earth-water.png", "L"), (4096, 2048), interpolation=cv2.INTER_CUBIC)
    elif name == "topo": t = cv2.resize(ld(G + "/img/earth-topology.png", "L"), (4096, 2048), interpolation=cv2.INTER_CUBIC)
    elif name == "topograd":
        z = cv2.GaussianBlur(tex("topo"), (0, 0), 1.0)
        t = np.stack([np.roll(z, -1, 1) - np.roll(z, 1, 1), np.roll(z, -1, 0) - np.roll(z, 1, 0)], -1)
    elif name == "cloud": t = np.asarray(Image.open(G + "/clouds/clouds.png").convert("RGBA"), f32)[..., 3] / 255
    elif name == "freeze":
        h, w = 1024, 2048
        lat = np.abs(np.linspace(90, -90, h))[:, None] / 90
        wat = cv2.resize(tex("water"), (w, h), interpolation=cv2.INTER_AREA)
        topo = cv2.resize(tex("topo"), (w, h), interpolation=cv2.INTER_AREA)
        t = np.clip(0.62 - 0.42 * lat + 0.30 * wat - 0.35 * topo + 0.10 * fbm2((h, w), 77, 2.2), 0, 1).astype(f32)
    elif name == "icefx":
        a = fbm2((2048, 4096), 81, 1.7); b = fbm2((2048, 4096), 82, 1.5); c = fbm2((2048, 4096), 83, 2.3)
        cr = np.clip(1 - np.abs(b) / 0.05, 0, 1) * np.clip(c * 0.8 + 0.5, 0, 1) + 0.6 * np.clip(1 - np.abs(a + 0.3 * b) / 0.03, 0, 1)
        t = np.stack([np.clip(0.5 + 0.35 * a + 0.25 * c, 0, 1.3), np.clip(cv2.GaussianBlur(cr, (0, 0), 0.7), 0, 1)], -1).astype(f32)
    _tex[name] = t; return t


def sample(t, lat, lon, interp=cv2.INTER_LINEAR):
    h, w = t.shape[:2]
    mx = ((lon / (2 * np.pi) + 0.5) % 1.0 * w).astype(f32); my = ((0.5 - lat / np.pi) * (h - 1)).astype(f32)
    return cv2.remap(t, mx, my, interp, borderMode=cv2.BORDER_WRAP)


def rot_y(a): c, s = math.cos(a), math.sin(a); return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
def rot_x(a): c, s = math.cos(a), math.sin(a); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
def rot_z(a): c, s = math.cos(a), math.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


class Geo:
    def __init__(s, cx, cy, R, body, w, h, pad=0.0):
        P = int(R * pad) + 3
        s.x0 = max(0, int(cx - R) - P); s.x1 = min(w, int(cx + R) + P + 1); s.y0 = max(0, int(cy - R) - P); s.y1 = min(h, int(cy + R) + P + 1)
        s.ok = s.x1 > s.x0 and s.y1 > s.y0
        if not s.ok: return
        ys, xs = np.mgrid[s.y0:s.y1, s.x0:s.x1].astype(f32)
        s.u = (xs + 0.5 - cx) / R; s.v = -(ys + 0.5 - cy) / R
        s.rr = s.u * s.u + s.v * s.v; s.r = np.sqrt(s.rr); s.z = np.sqrt(np.clip(1 - s.rr, 0, 1)); s.R = R; s.body = body
        s.alpha = np.clip((1 - s.r) * R + 0.5, 0, 1)
        k = np.where(s.r > 0.9985, 0.9985 / np.maximum(s.r, 1e-6), 1.0).astype(f32)
        uu, vv = s.u * k, s.v * k; zz = np.sqrt(np.clip(1 - uu * uu - vv * vv, 0, 1))
        B = np.asarray(body, f32)
        bx = B[0, 0] * uu + B[1, 0] * vv + B[2, 0] * zz; by = B[0, 1] * uu + B[1, 1] * vv + B[2, 1] * zz; bz = B[0, 2] * uu + B[1, 2] * vv + B[2, 2] * zz
        s.lat = np.arcsin(np.clip(by, -1, 1)); s.lon = np.arctan2(bx, bz); s.n = (uu, vv, zz)
    def dot(s, L): return s.n[0] * f32(L[0]) + s.n[1] * f32(L[1]) + s.n[2] * f32(L[2])
    def tangent_basis(s):
        B = np.asarray(s.body, f32); cl, sl = np.cos(s.lon), np.sin(s.lon); cla, sla = np.cos(s.lat), np.sin(s.lat)
        eb = (cl, np.zeros_like(cl), -sl); nb = (-sla * sl, cla, -sla * cl)
        E = tuple(B[i, 0] * eb[0] + B[i, 1] * eb[1] + B[i, 2] * eb[2] for i in range(3))
        Nn = tuple(B[i, 0] * nb[0] + B[i, 1] * nb[1] + B[i, 2] * nb[2] for i in range(3))
        return E, Nn


def put(dst, g, rgb, alpha):
    sl = (slice(g.y0, g.y1), slice(g.x0, g.x1)); a = alpha[..., None]; dst[sl] = dst[sl] * (1 - a) + rgb * a
def addto(dst, g, rgb): dst[g.y0:g.y1, g.x0:g.x1] += rgb


RAY = np.array([0.20, 0.42, 1.0], f32)
def earth(dst, cx, cy, R, lon0, L=(0.0, 0.0, 1.0), sun=0.0, tilt=23.4, tip=12.0, cloud_t=0.0, amb=0.0, frost=0.0, lights=1.0,
          cloud_amt=1.0, atmo=1.0, amb_dir=(-0.5, 0.45, 0.74), rim=0.0):
    """sun: sunlight (0 = gone). amb: faint fill so the dark globe reads (label it 'brightened'). frost 0..1.
    lights: city lights over the whole globe (the Sun is gone). rim: faint blue airglow rim for the unlit planet."""
    H, W = dst.shape[:2]
    body = rot_z(math.radians(-tilt)) @ rot_x(math.radians(tip)) @ rot_y(-lon0)
    g = Geo(cx, cy, R, body, W, H, pad=0.10)
    if not g.ok: return None
    L = norm(L); ndl = g.dot(L)
    day = np.maximum(sample(tex("day"), g.lat, g.lon, cv2.INTER_CUBIC if R > 500 else cv2.INTER_LINEAR), 0)
    wat = sample(tex("water"), g.lat, g.lon)
    gr = sample(tex("topograd"), g.lat, g.lon)
    E, Nn = g.tangent_basis(); kb = 26.0
    cl_lon = g.lon - cloud_t * (0.6 + 0.4 * np.cos(g.lat * 2))
    cl = sample(tex("cloud"), g.lat, cl_lon) * cloud_amt
    if frost > 0:
        fo = sample(tex("freeze"), g.lat, g.lon)
        ice = smooth(fo - 0.06, fo + 0.06, f32(frost * 1.15))
        tone = sample(tex("topo"), g.lat, g.lon); fxv = sample(tex("icefx"), g.lat, g.lon)
        icec = (np.array([0.60, 0.69, 0.80], f32) + 0.30 * tone[..., None]) * (0.62 + 0.5 * day.mean(2, keepdims=True) ** 0.3) * (0.72 + 0.5 * fxv[..., 0:1])
        icec = icec * (1 - 0.55 * fxv[..., 1:2]) + np.array([0.10, 0.22, 0.36], f32) * 0.55 * fxv[..., 1:2]
        day = day * (1 - ice[..., None]) + icec * ice[..., None]
        wat = wat * (1 - ice)
    surf = np.zeros(day.shape, f32)
    if sun > 0:
        ndl_b = ndl - kb * (gr[..., 0] * (E[0] * L[0] + E[1] * L[1] + E[2] * L[2]) - gr[..., 1] * (Nn[0] * L[0] + Nn[1] * L[1] + Nn[2] * L[2]))
        mu = np.clip(ndl, 0, 1); trans = np.exp(-np.multiply.outer(1.0 / (mu + 0.06), np.array([0.035, 0.085, 0.20], f32) * atmo))
        wrap = smooth(-0.10, 0.16, ndl); lam = np.clip(ndl_b, 0, 1) * wrap
        surf = day * lam[..., None] * trans * 1.25
        Hh = norm(L + np.array([0, 0, 1.0])); ndh = np.clip(g.dot(Hh), 0, 1)
        surf += (wat * (ndh ** 300 * 1.1 + ndh ** 36 * 0.07) * wrap * (1 - cl))[..., None] * np.array([1.0, 0.93, 0.80], f32) * trans
        surf = surf * (1 - cl[..., None] * 0.92) + (cl ** 0.75 * (mu * 0.92 + 0.08) * wrap)[..., None] * trans * 1.05
        zz = np.maximum(g.z, 0.02); air = (1 - np.exp(-0.10 * atmo / zz))
        surf = surf * (1 - 0.55 * air[..., None] * RAY) + (air * smooth(-0.18, 0.25, ndl) * 0.62)[..., None] * RAY
        surf *= sun
    if lights > 0:
        nl = np.maximum(sample(tex("night"), g.lat, g.lon, cv2.INTER_CUBIC if R > 500 else cv2.INTER_LINEAR), 0)
        dark = 1 - smooth(-0.12, 0.10, ndl) * min(1.0, sun)
        lum = np.clip(nl[..., 0] - 0.012, 0, 1)
        surf += (lum * dark * (1 - 0.75 * cl) * 3.2 * lights)[..., None] * np.array([1.0, 0.62, 0.26], f32)
    if amb > 0:
        base = day * 0.8 + 0.02 + (cl * 0.6)[..., None]
        La = norm(amb_dir); nda = g.dot(La) - kb * 1.6 * (gr[..., 0] * (E[0] * La[0] + E[1] * La[1] + E[2] * La[2]) - gr[..., 1] * (Nn[0] * La[0] + Nn[1] * La[1] + Nn[2] * La[2]))
        surf += base * amb * np.array([0.55, 0.70, 1.0], f32) * (0.22 + 1.05 * np.clip(nda, 0, 1) ** 0.8 * smooth(-0.1, 0.25, g.dot(La)))[..., None]
    if rim > 0:                                                    # thin airglow / scattered starlight limb
        zz = np.maximum(g.z, 0.02)
        surf += ((1 - np.exp(-0.06 / zz)) * rim)[..., None] * np.array([0.25, 0.55, 1.0], f32) * 0.05
    put(dst, g, surf, g.alpha)
    if rim > 0:
        hgt = (g.r - 1) * R
        hp = np.maximum(hgt, 0); outer = np.where(hgt > 0, np.exp(-hp / max(1.5, R * 0.006)) + 0.15 * np.exp(-hp / max(4.0, R * 0.025)), 0)
        addto(dst, g, (outer * rim * 0.035)[..., None] * np.array([0.25, 0.55, 1.0], f32))
    if sun > 0 and atmo > 0:
        hgt = (g.r - 1) * R; lim = (g.u * L[0] + g.v * L[1]) / np.maximum(g.r, 1e-3)
        illum = smooth(-0.35, 0.35, lim * math.hypot(L[0], L[1])) if abs(L[2]) < 0.999 else 1.0
        hp = np.maximum(hgt, 0); outer = np.where(hgt > 0, np.exp(-hp / max(1.6, R * 0.007)) + 0.16 * np.exp(-hp / max(5.0, R * 0.03)), 0)
        addto(dst, g, (outer * illum * atmo * sun * 0.9)[..., None] * RAY)
    return g


_sun = {}
def sun_disc(dst, cx, cy, R, t, power=1.0, corona=1.0, col=(1.0, 0.60, 0.22), gran_amp=0.22):
    """textured photosphere + chromosphere/prominences/corona (strong HDR)"""
    H, W = dst.shape[:2]
    if not _sun:
        _sun["g1"] = fbm2((1024, 2048), 11, 0.6, lo=40); _sun["g2"] = fbm2((1024, 2048), 12, 1.6, lo=6)
        _sun["g3"] = fbm2((1024, 2048), 13, 2.4)
        sp = lin(np.asarray(Image.open(TP + "/sunmap.jpg").convert("L"), f32)[..., None] / 255)[..., 0]
        _sun["spots"] = cv2.resize(sp, (2048, 1024), interpolation=cv2.INTER_CUBIC)
        _sun["ray"] = fbm2((512, 2048), 14, 2.7); _sun["ray2"] = fbm2((64, 4096), 15, 2.2)
    pad = 2.6 if corona > 0 else 0.1
    g = Geo(cx, cy, R, rot_z(math.radians(7)) @ rot_x(math.radians(5)) @ rot_y(-0.012 * t), W, H, pad=pad)
    if not g.ok: return None
    mu = g.z
    gran = sample(_sun["g1"], g.lat, g.lon + 0.0006 * t) * 0.5 + sample(_sun["g1"], g.lat + 0.3, g.lon - 0.0009 * t + 1.0) * 0.5
    meso = sample(_sun["g2"], g.lat, g.lon + 0.002 * t); big = sample(_sun["g3"], g.lat, g.lon)
    spots = sample(_sun["spots"], g.lat, g.lon, cv2.INTER_CUBIC)
    inten = 1 + gran_amp * gran * (0.4 + 0.6 * mu) + 0.10 * meso + 0.07 * big
    fac = np.clip(meso * 0.6 + big * 0.5 - 0.55, 0, 1) * (1 - mu) * 1.6
    inten = inten * (0.25 + 0.75 * np.clip(spots / 0.72, 0, 1) ** 1.6) + fac
    ld = np.stack([1 - c * (1 - mu) - 0.18 * (1 - mu) ** 2 for c in (0.42, 0.62, 0.80)], -1)
    disc = (np.maximum(inten, 0)[..., None] ** 1.5 * ld * np.array(col, f32) * 1.55 * power).astype(f32)
    ang = np.arctan2(g.v, g.u); h = np.maximum(g.r - 1, 0)
    if corona > 0:
        ax = ((ang / (2 * np.pi) + 0.5) * 2048).astype(f32); ry = np.clip(h / 2.6, 0, 1) * 511
        st1 = cv2.remap(_sun["ray"], ax, (ry * 0.25 + 3 * math.sin(t * 0.05)).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        st2 = cv2.remap(_sun["ray2"], ax * 2, (ry * 0.02 + 8).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        stream = np.clip(0.8 + 0.6 * st1 + 0.3 * st2, 0.05, 3) ** 1.6
        fall = 0.9 * np.exp(-h / 0.045) + 0.16 / (1 + (h / 0.13) ** 2.4) + 0.012 / (1 + (h / 0.7) ** 2.0)
        cor = (fall * (0.35 + 0.65 * stream * np.clip(h / 0.08, 0, 1)) * (g.r >= 1))[..., None] * np.array([1.0, 0.74, 0.46], f32) * 1.1 * corona * power
        prom = np.zeros_like(h)
        for a0, hh, ww, sd in ((0.62, 0.075, 0.06, 1), (2.45, 0.11, 0.045, 2), (-1.9, 0.05, 0.09, 3), (-0.55, 0.035, 0.05, 4), (3.9 - 2 * np.pi, 0.06, 0.035, 5)):
            da = (ang - a0 + np.pi) % (2 * np.pi) - np.pi
            arch = np.exp(-((h - hh * (1 - (da / ww) ** 2).clip(0, 1) ** 0.5 * (0.9 + 0.1 * math.sin(t * 0.3 + sd))) / (0.012 + 0.2 * hh)) ** 2) * (np.abs(da) < ww * 1.05)
            prom += arch * (0.55 + 0.45 * np.clip(st1 * 0.8 + 0.5, 0, 1.4))
        chrom = np.exp(-h / 0.008) * (g.r >= 1)
        cor += ((prom * 0.9 + chrom * 1.6) * (g.r >= 1))[..., None] * np.array([1.0, 0.20, 0.08], f32) * 1.6 * power
        addto(dst, g, cor.astype(f32))
    put(dst, g, disc, g.alpha)
    return g


def space_sky(stars, W, H, cx, cy, rot=0.0, scale=1.0, gain=1.0, plate_gain=0.8):
    """static star field + Milky Way: plate pixel (cx, cy) at frame centre; scale = plate px per frame px"""
    M = cv2.getRotationMatrix2D((0, 0), rot, scale)
    M[0, 2] = cx - (M[0, 0] * W / 2 + M[0, 1] * H / 2); M[1, 2] = cy - (M[1, 0] * W / 2 + M[1, 1] * H / 2)
    img = cv2.warpAffine(stars.plate, M, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_WRAP) * plate_gain
    Mi = cv2.invertAffineTransform(M)
    fx = Mi[0, 0] * stars.bx + Mi[0, 1] * stars.by + Mi[0, 2]; fy = Mi[1, 0] * stars.bx + Mi[1, 1] * stars.by + Mi[1, 2]
    ok = (fx > 0) & (fx < W - 1) & (fy > 0) & (fy < H - 1)
    acc = np.zeros((H + 1, W + 1, 3), f32)
    x0 = np.floor(fx[ok]).astype(int); y0 = np.floor(fy[ok]).astype(int); ux = (fx[ok] - x0)[:, None]; uy = (fy[ok] - y0)[:, None]
    val = stars.bf[ok, None] * stars.bc[ok]
    for dy, dx, w in ((0, 0, (1 - ux) * (1 - uy)), (0, 1, ux * (1 - uy)), (1, 0, (1 - ux) * uy), (1, 1, ux * uy)):
        np.add.at(acc, (y0 + dy, x0 + dx), val * w)
    acc = acc[:H, :W]
    st = cv2.GaussianBlur(acc, (0, 0), 0.65) * 2.6
    big = acc * (acc.max(2, keepdims=True) > 2.0)
    st += cv2.GaussianBlur(big, (0, 0), 1.6) * 1.4 + cv2.GaussianBlur(big, (0, 0), 5.0) * 0.8
    return (img + st) * gain


def lens_warp(img, cx, cy, thetaE, shadow=0.35, mask=None):
    """apply a point-mass lens centred at (cx, cy) with Einstein radius thetaE (px) to a background image.
    Surface brightness is conserved; the shadow (fraction of thetaE, enlarged for visibility) is black.
    mask (optional HxW 0..1): only warp where mask > 0 (e.g. background behind foreground objects)."""
    H, W = img.shape[:2]
    R = int(thetaE * 6)
    x0, x1, y0, y1 = max(0, int(cx - R)), min(W, int(cx + R)), max(0, int(cy - R)), min(H, int(cy + R))
    if x1 <= x0 or y1 <= y0: return img
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(f32)
    tx, ty = xx + 0.5 - cx, yy + 0.5 - cy
    r2 = tx * tx + ty * ty + 1e-3
    k = 1 - thetaE ** 2 / r2
    k = k * smooth(R, R * 0.7, np.sqrt(r2)) + (1 - smooth(R, R * 0.7, np.sqrt(r2)))  # fade the warp out at the patch edge
    mx = (cx + tx * k - 0.5).astype(f32); my = (cy + ty * k - 0.5).astype(f32)
    out = img.copy()
    patch = cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    patch *= smooth(shadow * thetaE - 0.8, shadow * thetaE + 0.8, np.sqrt(r2))[..., None]
    out[y0:y1, x0:x1] = patch
    return out
