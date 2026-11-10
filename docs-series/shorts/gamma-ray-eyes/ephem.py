"""Sky orientation for the park: real Sun / Moon positions and the local-horizon -> galactic rotation at a real place and
time (astropy; no network: bundled IERS tables). Run once: writes SCR/ephem.npz (per-frame matrices + Sun/Moon vectors).
  search : PYTHONPATH=SCR/pylib python -I ephem.py search      (scan dates for a good composition)
  write  : PYTHONPATH=SCR/pylib python -I ephem.py write       (per-frame tables for the chosen moment)"""
import os, sys
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S3-gamma-ray-eyes"
sys.path.insert(0, os.path.join(SCR, "pylib"))
import numpy as np
import warnings; warnings.filterwarnings("ignore")
from astropy.utils import iers
iers.conf.auto_download = False; iers.conf.auto_max_age = None
import astropy.units as u
from astropy.time import Time
from astropy.coordinates import EarthLocation, AltAz, SkyCoord, get_body, Galactic

# chosen moment (scan with `search` + previews): Cape Town latitude, 16 Jan 2026, 08:00 local (06:00 UTC), looking
# east-north-east. The waning crescent Moon (29 deg from the Sun) is ~53 deg up, right beside the Galactic Centre, so
# the inner Milky Way runs diagonally through the frame; the Sun is ~24 deg up above the houses.
SITE = dict(lat=-33.9, lon=18.4)
T0 = "2026-01-16T06:00:00"          # UTC
SPEED = 30.0                       # sky clock runs 30x real time (slow visible rotation over the Short)


def enu_to_gal(times, site=SITE):
    """3x3 matrices M (n,3,3) with gal_vec = M @ enu_vec (enu = east, north, up)"""
    loc = EarthLocation(lat=site["lat"] * u.deg, lon=site["lon"] * u.deg, height=0 * u.m)
    n = len(times); fr = AltAz(obstime=times, location=loc)
    cols = []
    for alt, az in ((0, 90), (0, 0), (90, 0)):
        c = SkyCoord(alt=np.full(n, alt) * u.deg, az=np.full(n, az) * u.deg, frame=fr).transform_to(Galactic())
        cols.append(c.cartesian.xyz.value.T)
    return np.stack(cols, 2)


def body_enu(name, times, site=SITE):
    loc = EarthLocation(lat=site["lat"] * u.deg, lon=site["lon"] * u.deg, height=0 * u.m)
    c = get_body(name, times, loc).transform_to(AltAz(obstime=times, location=loc))
    alt, az = c.alt.rad, c.az.rad
    return np.stack([np.cos(alt) * np.sin(az), np.cos(alt) * np.cos(az), np.sin(alt)], 1)


def search():
    """print candidate moments: Sun alt 35-75, Moon alt 30-75, elongation 45-80 deg, galactic centre near the Sun"""
    best = []
    for lat in (-33.9,):
        site = dict(lat=lat, lon=18.4)
        ts = Time("2026-01-01T00:00:00") + np.arange(0, 365 * 24 * 2) * 0.5 * u.hour
        loc = EarthLocation(lat=lat * u.deg, lon=18.4 * u.deg)
        sun = body_enu("sun", ts, site); moon = body_enu("moon", ts, site)
        el = np.degrees(np.arccos(np.clip((sun * moon).sum(1), -1, 1)))
        sa, ma = np.degrees(np.arcsin(sun[:, 2])), np.degrees(np.arcsin(moon[:, 2]))
        ok = (sa > 35) & (sa < 75) & (ma > 30) & (ma < 75) & (el > 45) & (el < 80)
        idx = np.where(ok)[0]
        if not len(idx): continue
        M = enu_to_gal(ts[idx], site)
        gs = np.einsum("nij,nj->ni", M, sun[idx]); gm = np.einsum("nij,nj->ni", M, moon[idx])
        gc = np.degrees(np.arccos(np.clip(gs[:, 0], -1, 1)))         # Sun - galactic centre separation
        bm = np.degrees(np.arcsin(gm[:, 2]))
        for k, i in enumerate(idx):
            best.append((gc[k], ts[i].isot, lat, round(sa[i], 1), round(ma[i], 1), round(el[i], 1), round(bm[k], 1)))
    best.sort()
    for b in best[:25]: print(b)


def write(dur=40.0, fps=30):
    n = int(dur * fps) + 2
    ts = Time(T0) + (np.arange(n) / fps * SPEED) * u.s
    M = enu_to_gal(ts)
    sun = body_enu("sun", ts); moon = body_enu("moon", ts)
    np.savez(os.path.join(SCR, "ephem.npz"), M=M.astype(np.float64), sun=sun, moon=moon, fps=fps, speed=SPEED, t0=T0)
    sa, ma = np.degrees(np.arcsin(sun[0, 2])), np.degrees(np.arcsin(moon[0, 2]))
    saz, maz = np.degrees(np.arctan2(sun[0, 0], sun[0, 1])), np.degrees(np.arctan2(moon[0, 0], moon[0, 1]))
    print("sun alt/az", sa, saz, "moon alt/az", ma, maz, "elong", np.degrees(np.arccos((sun[0] * moon[0]).sum())))


if __name__ == "__main__":
    search() if sys.argv[1] == "search" else write()
