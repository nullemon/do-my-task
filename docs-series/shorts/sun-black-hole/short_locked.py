"""VERSION B — LOCKED CAMERA. One tripod frame of the park for the whole Short; everything happens in that sky:
the Sun swells, flickers and implodes to a point (time-compressed illustration), a flash, instant night, stars fade in,
the black hole hangs where the Sun was (enlarged; the real night sky is lensed around it with the exact point-lens map
while the stars drift past in time-lapse, forming image pairs and an Einstein ring), then the frost. Same voice/captions/music.
Usage: /home/user/ttsenv/bin/python short_locked.py vert|wide [t1,t2,...]
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import short as A
from short import *                      # noqa: F401,F403  (timeline constants, Scene, helpers)
import numpy as np, cv2
from PIL import Image
from lib.core import f32, ease, ramp, smooth, noise1, splat
from lib.sky import day_sky, sun_disc, lens_flare
from lib import space as SP
from lib.post import bloom, tonemap, finish, Encoder, handheld
from lib.text import hud_text

T_SW0 = LN["then"]["start"]                          # swelling / flicker begins
T_COLL = A.T_COL0 + 0.25                             # implosion begins
T_FLASH = T_OUT - 0.10
V_DRIFT = (-20.0, 7.0)                               # px/s apparent drift of the stars past the black hole (time-lapse)


class Locked(A.Scene):
    def __init__(self, vertical=True):
        super().__init__(vertical)
        self.thE = 105.0 if vertical else 85.0          # Einstein radius drawn in px (real: ~0.23 px -> ~450x enlarged)
        self.bh = self.sun
        # bright background stars that drift into near-alignment (frame px offsets of their closest approach, time)
        self.heroes = [(A.wt("bh", "6 KM"), 9.0, 22.0), (A.wt("scope", "BENDING"), 2.0, 30.0), (A.wt("end", "FROZEN"), 14.0, 16.0)]

    def st(self, t):
        s = super().st(t)
        s["inset"] = 0.0; s["marker"] = 0.0; s["orbit"] = 0.0; s["zoom"] = 1.0
        s["shot"] = "park"; s["t0"] = 0.0
        return s

    def cam_xy(self, t, x, y): return x, y

    def sun_state(self, t):
        """(radius scale, power, sky-light level, flash)"""
        if t >= T_OUT: return 0, 0, 0, 0
        if t < T_SW0: return 1.0, 1.0, 1.0, 0.0
        if t < T_COLL:                                          # swelling + flicker
            u = (t - T_SW0) / (T_COLL - T_SW0)
            fl = 1 + 0.25 * u * noise1(t, 77, 7.0, 2)
            return 1 + 0.9 * ease(u), (1 + 0.6 * ease(u)) * fl, 1.0 + 0.15 * ease(u), 0.0
        if t < T_FLASH:                                          # implosion: shrinks to a point, surface blazes
            u = (t - T_COLL) / (T_FLASH - T_COLL)
            r = max(1.9 * (1 - ease(u) ** 0.8) ** 1.5, 0.08)
            return r, min(1.6 / r ** 1.6, 60.0), 1.15 - 0.25 * u, 0.0
        f = math.exp(-(t - T_FLASH) / 0.035)
        return 0.06, 60.0, 0.9, f

    def sky_night(self, t, s):
        W, H = self.L.W, self.L.H
        dt = t - T_OUT
        sh = (V_DRIFT[0] * dt, V_DRIFT[1] * dt)
        sky = self.stars.render(self.cam, t, cx=2020, cy=1180, rot=-8, gain=1.0, twinkle=1.0, plate_gain=0.6, shift=sh)
        bx, by = self.bh
        for (ta, imp, flux) in self.heroes:                      # extra background stars passing behind the hole
            px = bx + V_DRIFT[0] * (t - ta) - imp * 0.33; py = by + V_DRIFT[1] * (t - ta) + imp
            if abs(px - bx) < 700 and abs(py - by) < 700:
                splat(sky, px, py, 14, lambda d, dx, dy: (np.exp(-d * d / (2 * 1.6 ** 2)) * flux * 0.25)[..., None] * np.array([0.85, 0.92, 1.0], f32))
        # a faint, distant galaxy almost exactly behind the hole (its own slow drift): lensed into the Einstein ring
        ox, oy = 5.0 * math.sin(0.21 * t), 4.0 * math.cos(0.17 * t)
        splat(sky, bx + ox, by + oy, 40, lambda d, dx, dy: (np.exp(-d * d / (2 * 5.0 ** 2)) * 0.05 + np.exp(-d / 9.0) * 0.012)[..., None] * np.array([1.0, 0.88, 0.72], f32))
        return SP.lens_warp(sky, bx, by, self.thE, shadow=0.40)

    def frame(self, t):
        L = self.L; W, H = L.W, L.H; s = self.st(t); fg = self.fg
        sx, sy = self.sun
        img = np.zeros((H, W, 3), f32)
        rs, pw, skyl, flash = self.sun_state(t)
        a = fg.a[..., None]
        if t < T_OUT:
            img += day_sky(self.cam, sx, sy, t, skyl, cirrus=0.0)
            sun_disc(img, sx, sy, self.sun_r * max(rs, 0.05), pw)
            if t > T_SW0 and t < T_FLASH:                        # the swelling Sun's outer glow, contracting in the implosion
                g = 1.0 if t < T_COLL else max(rs / 1.9, 0.0)
                splat(img, sx, sy, 260, lambda d, dx, dy: (np.exp(-d / (14 + 30 * g)) * 1.5 * g * min(pw, 3))[..., None] * np.array([1.0, 0.85, 0.65], f32))
            if flash > 0:
                splat(img, sx, sy, W * 1.5, lambda d, dx, dy: ((np.exp(-d / 3) * 600 + np.exp(-d / 60) * 30 + np.exp(-d / 500) * 3) * flash)[..., None] * np.array([0.92, 0.95, 1.0], f32))
            fgc = self.day_fg * (1 + 5.0 * flash * np.array([0.95, 1.0, 1.1], f32))
            img = img * (1 - a) + fgc * a
            lens_flare(img, sx, sy, min(pw, 4.0) * (1 + 6 * flash))
        else:
            img += self.sky_night(t, s)
            nl = 0.072
            cold = s["frost"]
            fgc = self.night_day * nl * (1 + cold * np.array([-0.10, 0.0, 0.18], f32))      # colder grade as it freezes
            fgc = fg.frost(fgc, cold, t, level=nl * 1.4)
            fgc = fg.lamps_light(fgc, s["lamps"], t)
            img = img * (1 - a) + fgc * a
            if s["lamps"] > 0 and cold > 0:                       # crisp halos / diffraction spikes in the dry, cold air
                for (lx, ly, _) in fg.lamps:
                    splat(img, lx, ly + 2, 140, lambda d, dx, dy: ((np.exp(-np.abs(dy) / 1.2) * np.exp(-np.abs(dx) / 45) + np.exp(-np.abs(dx) / 1.2) * np.exp(-np.abs(dy) / 30)) * 0.5 * cold * s["lamps"])[..., None] * np.array([1.0, 0.75, 0.45], f32))
            img *= max(s["night"], 0.0)
        # locked tripod: no handheld, only a 3-frame jolt at the impact
        if T_OUT <= t < T_OUT + 0.1:
            k = 1 - (t - T_OUT) / 0.1
            M = np.float32([[1, 0, 4 * k * math.sin(t * 90)], [0, 1, 5 * k]])
            img = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        img = bloom(img, 1.0 if t < T_OUT else 0.6)
        out = tonemap(img, 1.1 if t < T_OUT else 1.0)
        out = finish(out, t)
        self.overlay(out, t, s)
        self.facts(out, t)
        return out

    def facts(self, out, t):
        L = self.L; W = L.W; fs = int(L.hud_size * 0.40); bx, by = self.bh
        top = L.safe_top + 40 if L.vertical else 60
        low = 1235 if L.vertical else 720                   # facts row (clear of the hole, the caption and the counter)
        def lab(txt, x, y, a, col=(225, 232, 245), size=fs, wt="SemiBold", tr=0.18):
            if a > 0.01: hud_text(out, txt, x, y, size, wt, col, a, tr)
        a = ramp(t, T_SW0 + 0.2, T_SW0 + 0.5) * (1 - ramp(t, T_OUT + 1.0, T_OUT + 1.5))
        a = ramp(t, T_OUT + 2.5, T_OUT + 3.2)
        o0, o1 = LN["orbit"]["start"], LN["bh"]["start"]
        lab("SAME MASS · SAME ORBIT", W / 2, low, ramp(t, o0, o0 + 0.3) * (1 - ramp(t, o1 - 0.2, o1 + 0.1)), (195, 220, 255), int(fs * 1.15))
        b0, b1 = LN["bh"]["start"], LN["scope"]["start"]
        lab("EVENT HORIZON ≈ 6 KM ACROSS", W / 2, low, ramp(t, b0, b0 + 0.3) * (1 - ramp(t, b1 + 0.6, b1 + 0.9)), (255, 210, 160), int(fs * 1.1))
        c0, c1 = b1 + 0.9, LN["cold"]["start"]
        lab("NO DISK: NOTHING IS FALLING IN", W / 2, low, ramp(t, c0, c0 + 0.3) * (1 - ramp(t, c1 - 0.2, c1 + 0.1)), (215, 225, 240), int(fs * 1.1))
        lab("EINSTEIN RING · REAL SIZE ≈ 1.4′", W / 2, low + fs * 1.7, ramp(t, c0 - 0.6, c0) * (1 - ramp(t, c1 - 0.2, c1 + 0.1)) * 0.85, (200, 212, 232), int(fs * 0.85))


def run(vertical, stills=None):
    sc = Locked(vertical); tag = "locked_vert" if vertical else "locked_wide"
    if stills:
        os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
        for t in stills:
            t0 = time.time(); im = sc.frame(t)
            Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(SCR, "stills", f"{tag}_{t:05.2f}.png"))
            print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)
        return
    n = int(round(DUR * FPS))
    enc = Encoder(os.path.join(SCR, f"video_{tag}.mp4"), sc.L.W, sc.L.H, FPS, crf=16)
    t0 = time.time()
    for i in range(n):
        enc.write(sc.frame(i / FPS))
        if i % 60 == 0: print(f"{tag} frame {i}/{n}  {time.time() - t0:.0f}s", flush=True)
    enc.close(); print("done", time.time() - t0)


if __name__ == "__main__":
    vert = sys.argv[1] != "wide"
    st = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    run(vert, st)
