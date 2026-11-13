"""Star catalogue for the Short: HYG v4.1 (astronexus/HYG-Database, hyg/CURRENT/hygdata_v41.csv; Hipparcos + Yale BSC +
Gliese) -> SCR/stars.npz. Keeps every star brighter than V = 7.0 (RA, Dec, V mag, B-V, distance), the Sun excluded.
Usage: /home/user/ttsenv/bin/python catalog.py"""
import csv, os
import numpy as np
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B2-galaxies-visible"
SRC = os.path.join(SCR, "dl", "hygrepo", "hyg", "CURRENT", "hygdata_v41.csv")
LY_PER_PC = 3.26156

if __name__ == "__main__":
    ra, dec, mag, ci, dist, name = [], [], [], [], [], []
    for r in csv.DictReader(open(SRC)):
        if r["proper"] == "Sol" or not r["mag"]: continue
        m = float(r["mag"])
        if m >= 7.0: continue
        ra.append(float(r["ra"]) * 15.0); dec.append(float(r["dec"])); mag.append(m)
        ci.append(float(r["ci"]) if r["ci"] else 0.6); dist.append(float(r["dist"]) * LY_PER_PC); name.append(r["proper"])
    np.savez(os.path.join(SCR, "stars.npz"), ra=np.array(ra), dec=np.array(dec), mag=np.array(mag), ci=np.array(ci),
             ly=np.array(dist), name=np.array(name))
    print(len(ra), "stars; named:", sum(1 for n in name if n))
