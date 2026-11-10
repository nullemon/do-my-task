"""Moving-star catalogue for "Your Night Sky in 1 Million Years".
Source: HYG v4.1 (astronexus/HYG-Database, hyg/CURRENT/hygdata_v41.csv: Hipparcos + Yale BSC + Gliese), columns ra, dec,
dist (pc), pmra (mu_alpha*, mas/yr), pmdec (mas/yr), rv (km/s), mag, absmag, ci.
Every star gets a heliocentric 3D position (pc) and a straight-line 3D space velocity (pc/yr) built from its parallax
distance, proper motion and radial velocity (rv = 0 where HYG has none). Kept: every star with V < 7 today, plus any star
that gets brighter than V = 7 at some point within the next 1.35 Myr.
Overrides (HYG placeholders / pre-Gaia values):
  Barnard's Star  HYG pmdec is the 9999.99 placeholder -> Gaia DR3: pmra -801.551, pmdec 10362.394 mas/yr,
                  parallax 546.976 mas, rv -110.5 km/s
  Gliese 710      Hipparcos pm/rv are too coarse for the encounter -> a trajectory that reproduces the Gaia DR3 result
                  (closest approach 0.051 pc ~ 10,500 au, 1.29 Myr from now; Wikipedia / de la Fuente Marcos 2022),
                  starting from its present place and distance (parallax 52.4 mas = 19.08 pc)
Usage: /home/user/ttsenv/bin/python catalog.py   -> SCR/moving.npz"""
import csv, os, math
import numpy as np
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S10-sky-1myr"
SRC = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S5-star-dates/dl/hygrepo/hyg/CURRENT/hygdata_v41.csv"
KMS = 1.0 / 977792.2          # 1 km/s in pc/yr
TMAX = 1.35e6


def unit(ra_deg, dec_deg):
    a, d = np.radians(ra_deg), np.radians(dec_deg)
    return np.stack([np.cos(d) * np.cos(a), np.cos(d) * np.sin(a), np.sin(d)], -1)


def state(ra, dec, dist, pmra, pmdec, rv):
    """heliocentric position (pc) and velocity (pc/yr), ICRS axes"""
    a, d = np.radians(ra), np.radians(dec)
    u = unit(ra, dec)
    e = np.stack([-np.sin(a), np.cos(a), np.zeros_like(a)], -1)                       # east
    n = np.stack([-np.sin(d) * np.cos(a), -np.sin(d) * np.sin(a), np.cos(d)], -1)     # north
    k = 4.740470 * dist                                                                   # km/s per (arcsec/yr)
    v = (u * rv[..., None] + e * (k * pmra / 1000)[..., None] + n * (k * pmdec / 1000)[..., None]) * KMS
    return u * dist[..., None], v


if __name__ == "__main__":
    rows = []
    for r in csv.DictReader(open(SRC)):
        if r["proper"] == "Sol" or not r["mag"] or not r["dist"]: continue
        d = float(r["dist"])
        if d <= 0 or d >= 99999: continue
        rows.append(r)
    ra = np.array([float(r["ra"]) * 15 for r in rows]); dec = np.array([float(r["dec"]) for r in rows])
    dist = np.array([float(r["dist"]) for r in rows]); mag = np.array([float(r["mag"]) for r in rows])
    pmra = np.array([float(r["pmra"] or 0) for r in rows]); pmdec = np.array([float(r["pmdec"] or 0) for r in rows])
    rv = np.array([float(r["rv"] or 0) for r in rows]); ci = np.array([float(r["ci"]) if r["ci"] else 0.6 for r in rows])
    hip = np.array([int(r["hip"]) if r["hip"] else 0 for r in rows]); name = np.array([r["proper"] for r in rows])
    con = np.array([r["con"] for r in rows]); bayer = np.array([r["bayer"] for r in rows])
    # overrides
    b = np.where(hip == 87937)[0][0]                       # Barnard's Star (Gaia DR3)
    pmra[b], pmdec[b], dist[b], rv[b] = -801.551, 10362.394, 1000 / 546.976, -110.5
    g = np.where(hip == 89825)[0][0]                       # Gliese 710
    dist[g] = 1000 / 52.4
    pos, vel = state(ra, dec, dist, pmra, pmdec, rv)
    T, bmin = 1.29e6, 0.051
    u = pos[g] / dist[g]
    side = np.cross(u, [0, 0, 1.0]); side /= np.linalg.norm(side)
    vel[g] = (-pos[g] + side * bmin) / T                   # straight line through (0.051 pc off the Sun) at t = 1.29 Myr
    absm = mag - 5 * np.log10(dist / 10)
    vt = np.linalg.norm(vel, axis=1) / KMS
    ok = vt < 400                                          # drop absurd space velocities (bad parallaxes)
    # minimum distance within [0, TMAX] -> brightest magnitude
    tc = np.clip(-(pos * vel).sum(1) / np.maximum((vel * vel).sum(1), 1e-30), 0, TMAX)
    dmin = np.linalg.norm(pos + vel * tc[:, None], axis=1)
    dend = np.linalg.norm(pos + vel * TMAX, axis=1)
    mmin = absm + 5 * np.log10(np.minimum(np.minimum(dmin, dend), dist) / 10)
    keep = ok & ((mag < 7.0) | (mmin < 7.0))
    keep[b] = keep[g] = True
    idx = np.where(keep)[0]
    np.savez(os.path.join(SCR, "moving.npz"), pos=pos[idx], vel=vel[idx], absm=absm[idx], mag=mag[idx], ci=ci[idx],
             hip=hip[idx], name=name[idx], con=con[idx], bayer=bayer[idx], ra=ra[idx], dec=dec[idx])
    print(len(idx), "stars kept;", int(((mag >= 7.0) & keep).sum()), "of them become naked-eye later")
    for h in (87937, 89825, 91262, 97649, 71683, 32349):
        i = np.where(hip == h)[0][0]
        print(f"{str(name[i] or h):16s} now V={mag[i]:5.2f} d={dist[i]:6.2f}pc  closest {dmin[i]:.3f} pc at {tc[i]/1e3:7.1f} kyr  V_min={mmin[i]:5.2f}")
