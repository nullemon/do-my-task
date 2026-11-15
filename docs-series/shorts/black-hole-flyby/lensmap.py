"""Weak-field lens map for the telescope inset, built with ../black-hole-suns/lens.py (exact Schwarzschild null geodesics).
For a 10 M_sun hole seen from 0.5 AU (r_obs = 2.5 million Rs) the traced table alpha -> alpha_sky is expressed in units of
the Einstein angle theta_E = sqrt(2 / r_obs) rad: y(x) = beta / theta_E as a function of x = theta / theta_E. Far from the
photon sphere this curve is universal (point lens), so one traced table serves every distance in the Short.
y > 0: the source lies on the same side as the image; y < 0: the ray passed on the far side (the inner image)."""
import os, sys, math
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "black-hole-suns"))
import lens

RS_KM = 2.9533 * 10.0
AU_KM = 1.495978707e8
CACHE = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B4-black-hole-flyby/lens_table.npz"


def table():
    if os.path.exists(CACHE):
        z = np.load(CACHE); return z["x"], z["y"]
    r_obs = 0.5 * AU_KM / RS_KM; thE = math.sqrt(2 / r_obs)
    tr = lens.Tracer(r_obs, a_max=12 * thE, n=3000, dphi=0.002, phi_max=1.2 * math.pi)
    ok = tr.esc
    x = tr.alpha[ok] / thE; y = tr.alpha_sky[ok] / thE
    os.makedirs(os.path.dirname(CACHE), exist_ok=True); np.savez(CACHE, x=x, y=y)
    return x, y


if __name__ == "__main__":
    x, y = table()
    for xi in (0.12, 0.3, 0.5, 1.0, 1.5, 2.0, 5.0, 10.0):
        print(f"x={xi:5.2f}  traced y={np.interp(xi, x, y):+.4f}  point-lens x-1/x={xi - 1 / xi:+.4f}")
