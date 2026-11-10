"""Locked timeline for "FRIDAY THE 13TH, 2029" (seconds, 24 fps) + the physical flyby model used by the true-scale shots."""
import math
import numpy as np
FPS = 24
DUR = 318.0
NFR = int(round(DUR * FPS))
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/10-apophis-2029"

# voice line starts (measured Kokoro durations in audio/placement.json)
START = {'hook1': 1.0, 'hook2': 10.0, 'disc1': 23.0, 'disc2': 33.9, 'scare': 40.2, 'name': 59.0, 'relief1': 65.2, 'relief2': 81.6,
         'size1': 95.6, 'size2': 111.4, 'scale1': 118.0, 'scale2': 132.8, 'pass1': 138.0, 'rare': 152.6, 'view1': 161.0,
         'view2': 175.6, 'view3': 188.4, 'grav1': 195.6, 'grav2': 211.0, 'miss1': 223.6, 'miss2': 237.6, 'hypo1': 255.8,
         'hypo2': 272.2, 'end1': 279.5, 'end2': 292.0, 'end3': 298.8, 'end4': 304.4}

# shots: (name, start, end); neighbours cross-fade over XF seconds centred on the boundary
XF = 0.8
SHOTS = [("hook", 0.0, 22.4), ("disc", 22.4, 39.6), ("scare", 39.6, 58.6), ("name", 58.6, 64.6), ("relief", 64.6, 94.6),
         ("size", 94.6, 116.8), ("geo", 116.8, 132.4), ("moon", 132.4, 137.4), ("pass", 137.4, 160.2), ("night", 160.2, 175.0),
         ("ground1", 175.0, 194.4), ("orbit", 194.4, 210.4), ("tides", 210.4, 222.8), ("miss", 222.8, 254.8), ("hypo", 254.8, 278.4),
         ("endpass", 278.4, 291.4), ("ground2", 291.4, 298.3), ("rock", 298.3, 303.8), ("ground3", 303.8, DUR)]

# ------------------------------------------------------------------ physical model (equatorial frame, km, hours from closest approach)
MU = 398600.4418
RE = 6371.0
R_GEO = 42164.0
R_MOON = 384400.0
RP = 38000.0            # perigee distance from Earth's centre (~31,600 km above the surface)
VINF = 5.84             # km/s  -> 7.42 km/s at perigee
A_H = MU / VINF ** 2
E_H = 1 + RP / A_H
GMST0 = math.radians(169.2)                 # Greenwich sidereal angle at 21:46 UTC, 13 April 2029 (approx.)
OMEGA = math.radians(15.041)                # rad per hour
SUN = np.array([math.cos(math.radians(9.2)) * math.cos(math.radians(21.8)), math.cos(math.radians(9.2)) * math.sin(math.radians(21.8)), math.sin(math.radians(9.2))])


def _unit(v): return v / np.linalg.norm(v)


def _rot(axis, ang):
    a = _unit(np.asarray(axis, float)); K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * K @ K


def lonlat(lon_deg, lat_deg, gm=GMST0):
    lo = math.radians(lon_deg) + gm; la = math.radians(lat_deg)
    return np.array([math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)])


P_HAT = lonlat(-42.0, 27.0)                 # sub-asteroid point at closest approach: mid-Atlantic, north of the equator (approx.)
_q0 = _unit(SUN - (SUN @ P_HAT) * P_HAT)    # leaves roughly toward the Sun, arrives from the night side
Q_HAT = _rot(P_HAT, math.radians(-38.0)) @ _q0


def apophis(tau_h):
    """geocentric position (km) at tau hours from closest approach, on the hyperbola"""
    n = math.sqrt(MU / A_H ** 3) * 3600.0
    Mh = n * tau_h; F = math.asinh(Mh / E_H) if abs(Mh) < 5 else math.copysign(math.log(2 * abs(Mh) / E_H + 1.8), Mh)
    for _ in range(40):
        F -= (E_H * math.sinh(F) - F - Mh) / (E_H * math.cosh(F) - 1)
    x = A_H * (E_H - math.cosh(F)); y = A_H * math.sqrt(E_H ** 2 - 1) * math.sinh(F)
    return x * P_HAT + y * Q_HAT


def speed(tau_h):
    r = np.linalg.norm(apophis(tau_h)); return math.sqrt(VINF ** 2 + 2 * MU / r)


if __name__ == "__main__":
    print("e", E_H, "a", A_H, "v_perigee", speed(0), "deflection deg", 2 * math.degrees(math.asin(1 / E_H)))
    for tau in (-8, -5, -3, -2, -1, -0.5, 0, 0.5, 1, 2, 4):
        p = apophis(tau); r = np.linalg.norm(p); gm = GMST0 + OMEGA * tau
        lon = (math.degrees(math.atan2(p[1], p[0]) - gm) + 540) % 360 - 180; lat = math.degrees(math.asin(p[2] / r))
        print(f"tau {tau:5.1f} h  r {r:9.0f} km  alt {r-6378:8.0f}  sub-point lon {lon:7.1f} lat {lat:6.1f}  v {speed(tau):.2f}  sun-angle {math.degrees(math.acos(p@SUN/r)):.0f}")
