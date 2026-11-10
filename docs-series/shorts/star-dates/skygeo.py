"""Real sky geometry for a locked camera: horizon frame (x = East, y = North, z = Up) at latitude LAT, local sidereal
time LST (hours) turns the celestial sphere about the true pole. The lens is a tilted stereographic projection
(conformal: star patterns keep their shapes; wide field with a straight-ish horizon behind the mountains)."""
import math
import numpy as np
from lib.core import f32

LAT = 47.0                                    # a mid-northern-latitude valley (Alps / Carpathians latitude)
EQ2GAL = np.array([[-0.0548755604, -0.8734370902, -0.4838350155],
                   [0.4941094279, -0.4448296300, 0.7469822445],
                   [-0.8676661490, -0.1980763734, 0.4559837762]])        # J2000 equatorial -> galactic


def hdir(az, alt):
    az, alt = np.radians(az), np.radians(alt)
    return np.stack([np.sin(az) * np.cos(alt), np.cos(az) * np.cos(alt), np.sin(alt)], -1)


def eq_vec(ra_deg, dec_deg):
    a, d = np.radians(ra_deg), np.radians(dec_deg)
    return np.stack([np.cos(d) * np.cos(a), np.cos(d) * np.sin(a), np.sin(d)], -1)


def eq2hor(lst_h, lat=LAT):
    """3x3 matrix: equatorial cartesian -> horizon (E, N, U) at sidereal time lst_h"""
    th = math.radians(lst_h * 15.0); p = math.radians(lat)
    # hour-angle frame: rotate by LST about the pole; then tilt by latitude
    Rz = np.array([[math.cos(th), math.sin(th), 0], [-math.sin(th), math.cos(th), 0], [0, 0, 1]])   # -> (cosd cosH, -cosd sinH, sind)
    # (cH, -sH, s) -> E = -cosd sinH, N = sind cosp - cosd cosH sinp, U = sind sinp + cosd cosH cosp
    T = np.array([[0, 1, 0], [-math.sin(p), 0, math.cos(p)], [math.cos(p), 0, math.sin(p)]])
    return T @ Rz


class Lens:
    def __init__(self, W, H, az0, alt0, f, horizon_y):
        self.W, self.H, self.f = W, H, f
        self.d0 = hdir(az0, alt0); self.right = hdir(az0 + 90, 0.0); self.up = hdir(az0, alt0 + 90)
        self.cx = W / 2; self.cy = horizon_y - 2 * f * math.tan(math.radians(alt0) / 2)

    def project(self, v):
        """v (..., 3) horizon unit vectors -> x, y, valid"""
        c = v @ self.d0
        k = 2 * self.f / np.maximum(1 + c, 1e-3)
        return self.cx + k * (v @ self.right), self.cy - k * (v @ self.up), c > -0.6

    def rays(self, step=1):
        """unit horizon vectors for every pixel (H/step, W/step, 3)"""
        yy, xx = np.mgrid[0:self.H:step, 0:self.W:step].astype(np.float64) + 0.5 * step
        px = (xx - self.cx) / (2 * self.f); py = -(yy - self.cy) / (2 * self.f)
        r2 = px * px + py * py
        v = ((1 - r2)[..., None] * self.d0 + 2 * px[..., None] * self.right + 2 * py[..., None] * self.up) / (1 + r2)[..., None]
        return v.astype(f32)


def lens_for(vertical, hz):
    return Lens(1080, 1920, 180.0, 50.0, 740.0, hz + 10) if vertical else Lens(1920, 1080, 180.0, 50.0, 520.0, hz + 10)
