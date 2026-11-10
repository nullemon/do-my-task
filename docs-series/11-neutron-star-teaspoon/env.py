"""Equirect HDR environment for the Blender spoon/ring renders: the Earth seen from ~0.6 Earth radii up (day map, clouds,
limb glow), black sky with the Sun as a small very bright disc and a faint Milky Way band.  -> $SCR/tex/env_earth.hdr
Blender world: +Z up; the Earth's centre is toward -Z."""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from lib import *
Wm, Hm = 4096, 2048
SUN_W = norm([-0.62, -0.50, 0.42])          # world direction to the Sun (matches the sun lamp in blender/spoon.py)
ALT = 0.62                                  # altitude in Earth radii


def build():
    u = (np.arange(Wm, dtype=F32) + 0.5) / Wm; v = (np.arange(Hm, dtype=F32) + 0.5) / Hm
    U, V = np.meshgrid(u, v)
    az = (U - 0.5) * 2 * np.pi; el = (0.5 - V) * np.pi
    # Blender equirect: u = atan2(dy, -dx) / 2pi + 0.5
    d = np.stack([-np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)], -1)
    c = np.array([0, 0, -(1 + ALT)], F32)                      # Earth centre, radius 1
    b = d @ c; disc = b * b - (c @ c - 1)
    hit = (disc > 0) & (b > 0); tt = b - np.sqrt(np.clip(disc, 0, None))
    P = d * tt[..., None] - c; P /= np.linalg.norm(P, axis=-1, keepdims=True)
    # body frame: rotate so an interesting ocean/land mix is below
    Rb = rot_axis((0, 1, 0), math.radians(-52)) @ rot_axis((0, 0, 1), math.radians(205))
    Pb = P @ Rb.T.astype(F32)
    lat = np.arcsin(np.clip(Pb[..., 2], -1, 1)); lon = np.arctan2(Pb[..., 1], Pb[..., 0])
    day = samp(tex("day"), lat, lon); cl = samp(tex("cloud"), lat, lon)
    ndl = np.clip(P @ SUN_W.astype(F32), 0, 1); term = np.clip((P @ SUN_W.astype(F32) + 0.05) / 0.25, 0, 1)
    surf = day * (1 - cl[..., None]) + cl[..., None]
    mu = np.clip(-(P * d).sum(-1), 0.05, 1)
    ins = (1 - np.exp(-0.10 / mu))
    surf = surf * (ndl ** 0.8 * term)[..., None] * 3.2
    surf = surf * (1 - 0.5 * ins[..., None]) + ins[..., None] * np.array([0.30, 0.52, 1.0], F32) * 3.0 * term[..., None]
    out = np.zeros((Hm, Wm, 3), F32)
    out[hit] = surf[hit]
    # limb glow outside
    ang = np.arccos(np.clip(b / np.linalg.norm(c), -1, 1)); a0 = math.asin(1 / (1 + ALT))
    glow = np.exp(-np.clip(ang - a0, 0, None) / 0.012) * (~hit)
    out += glow[..., None] * np.array([0.3, 0.55, 1.0], F32) * 2.2 * np.clip(0.35 + (d @ SUN_W.astype(F32)), 0.1, 1)[..., None]
    # faint sky + Milky Way-like band so dark metal is not pure black
    band = np.exp(-((d @ norm([0.3, 0.2, 0.93]).astype(F32)) / 0.16) ** 2)
    out += (~hit)[..., None] * (0.012 + 0.05 * band[..., None]) * np.array([0.8, 0.9, 1.2], F32)
    # the Sun: small disc, very bright (Blender also has a sun lamp for crisp shadows; this gives the specular hit)
    sa = np.arccos(np.clip(d @ SUN_W.astype(F32), -1, 1))
    out += (np.exp(-(sa / 0.012) ** 2) * 0 + np.exp(-(sa / 0.06) ** 2) * 40 + np.exp(-(sa / 0.3) ** 2) * 0.6)[..., None] * np.array([1.0, 0.96, 0.9], F32)
    # two soft "studio" fill strips far from the Earth to shape the metal (subtle, bluish/warm)
    for dirv, wdt, colr, g in ((norm([0.75, -0.2, 0.62]), 0.22, (0.75, 0.9, 1.3), 1.6), (norm([0.1, 0.9, 0.45]), 0.16, (1.2, 1.0, 0.8), 0.9)):
        aa = np.arccos(np.clip(d @ dirv.astype(F32), -1, 1)); out += np.clip(1 - aa / wdt, 0, 1)[..., None] ** 0.5 * np.array(colr, F32) * g * 0.5
    os.makedirs(TEX, exist_ok=True)
    cv2.imwrite(TEX + "/env_earth.hdr", out[..., ::-1])
    cv2.imwrite(SCR + "/chk/env_earth.jpg", (np.clip(out, 0, 1) ** 0.5 * 255).astype(np.uint8)[::2, ::2, ::-1])


if __name__ == "__main__":
    build(); print("env ok")


def studio():
    """dark studio environment for the gold ring: soft boxes (warm key, cool rim, top strip) on near-black"""
    u = (np.arange(Wm // 2, dtype=F32) + 0.5) / (Wm // 2); v = (np.arange(Hm // 2, dtype=F32) + 0.5) / (Hm // 2)
    U, V = np.meshgrid(u, v); az = (U - 0.5) * 2 * np.pi; el = (0.5 - V) * np.pi
    d = np.stack([-np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)], -1)
    out = np.full(d.shape, 0.006, F32)
    def box(dirv, wx, wy, col, g, upv=(0, 0, 1)):
        c = norm(dirv).astype(F32); r = norm(np.cross(upv, c)).astype(F32); up = np.cross(c, r).astype(F32)
        x = (d @ r) / np.maximum(d @ c, 1e-3); y = (d @ up) / np.maximum(d @ c, 1e-3)
        m = np.clip((wx - np.abs(x)) / 0.05, 0, 1) * np.clip((wy - np.abs(y)) / 0.05, 0, 1) * ((d @ c) > 0)
        out[:] += m[..., None] * np.array(col, F32) * g * (0.75 + 0.25 * np.cos(y / wy * 1.5))[..., None]
    box((-0.7, -0.6, 0.5), 0.55, 0.9, (1.0, 0.86, 0.66), 7.0)
    box((0.9, 0.1, 0.25), 0.16, 1.2, (0.55, 0.75, 1.25), 9.0)
    box((0.1, 0.5, 0.95), 0.9, 0.22, (1.0, 0.95, 0.9), 5.0, upv=(0, 1, 0))
    box((0.2, -0.9, -0.5), 0.7, 0.3, (1.0, 0.55, 0.25), 1.6)
    out = cv2.GaussianBlur(out, (0, 0), 3)
    cv2.imwrite(TEX + "/env_studio.hdr", out[..., ::-1])


if __name__ == "__main__":
    studio(); print("studio ok")
