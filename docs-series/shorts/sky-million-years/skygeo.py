"""Real sky geometry for a locked camera: horizon frame (x = East, y = North, z = Up) at latitude LAT, local sidereal
time LST (hours) turns the celestial sphere about the true pole. The lens is a tilted stereographic projection
(conformal: star patterns keep their shapes; wide field with a straight-ish horizon behind the mountains)."""
import math
import numpy as np
from lib.core import f32

LAT = 34.0                                    # a mid-latitude mountain valley (~34 deg N)
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
    return Lens(1080, 1920, 180.0, 56.0, 700.0, hz + 10) if vertical else Lens(1920, 1080, 180.0, 68.0, 440.0, hz + 10)


# ------------------------------------------------------------------ "views" (sky orientation as a rotation matrix)
def lens_ray(lens, x, y):
    px = (x - lens.cx) / (2 * lens.f); py = -(y - lens.cy) / (2 * lens.f); r2 = px * px + py * py
    v = ((1 - r2) * lens.d0 + 2 * px * lens.right + 2 * py * lens.up) / (1 + r2)
    return v / np.linalg.norm(v)


def view_R(lens, x, y, ra, dec, roll=0.0):
    """rotation (equatorial unit vectors -> camera horizon frame) that puts (ra, dec) at pixel (x, y) with celestial north
    pointing `roll` degrees clockwise from screen-up (sky seen from inside: east is to the LEFT of north)"""
    d = lens_ray(lens, x, y)
    up = lens_ray(lens, x, y - 1.0) - d; up -= d * (up @ d); up /= np.linalg.norm(up)
    rt = np.cross(up, d)                                   # screen-right (check sign below)
    if (lens_ray(lens, x + 1.0, y) - d) @ rt < 0: rt = -rt
    r = math.radians(roll)
    n_s = math.cos(r) * up + math.sin(r) * rt              # where celestial north points on screen
    e_s = np.cross(n_s, d)                                 # candidate east
    if e_s @ (math.cos(r) * rt - math.sin(r) * up) > 0: e_s = -e_s      # east = left of north
    a, de = math.radians(ra), math.radians(dec)
    u = np.array([math.cos(de) * math.cos(a), math.cos(de) * math.sin(a), math.sin(de)])
    n = np.array([-math.sin(de) * math.cos(a), -math.sin(de) * math.sin(a), math.cos(de)])
    e = np.array([-math.sin(a), math.cos(a), 0.0])
    A = np.stack([u, n, e], 1); B = np.stack([d, n_s, e_s], 1)
    R = B @ A.T
    if np.linalg.det(R) < 0: raise ValueError("improper rotation")
    return R


def slerp_R(R0, R1, u):
    """shortest-path rotation interpolation"""
    from scipy.spatial.transform import Rotation, Slerp
    s = Slerp([0, 1], Rotation.from_matrix(np.stack([R0, R1])))
    return s([min(max(u, 0.0), 1.0)]).as_matrix()[0]
