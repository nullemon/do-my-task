"""Numbers for "What If a Black Hole Passed Through the Solar System?" (printed; see README).
Units: AU, years, solar masses (G = 4 pi^2). A 10 M_sun black hole arrives at v_inf = 50 km/s in the ecliptic plane.
Leapfrog (kick-drift-kick, adaptive by the closest pair) for the Sun, Earth, Jupiter, Neptune and the hole."""
import math
import numpy as np

G = 4 * math.pi ** 2
KMS = 1 / 4.7404                                   # km/s -> AU/yr
M_BH = 10.0
RS_KM = 2.9533 * M_BH                              # Schwarzschild radius (km)
AU_KM = 1.495978707e8


def orbit_el(r, v, mu=G):
    rn = np.linalg.norm(r); E = 0.5 * v @ v - mu / rn
    if E >= 0: return math.inf, math.inf
    a = -mu / (2 * E); h = r[0] * v[1] - r[1] * v[0]
    e = math.sqrt(max(0.0, 1 + 2 * E * h * h / mu ** 2)); return a, e


def run(b_au, phase_e=0.0, v_inf=50.0, start=400.0, years=60.0):
    m = np.array([1.0, 3.003e-6, 9.55e-4, 5.15e-5, M_BH])
    pos = np.zeros((5, 2)); vel = np.zeros((5, 2))
    for i, (a, ph) in enumerate(((1.0, phase_e), (5.203, 1.0), (30.07, 2.0)), start=1):
        pos[i] = a * np.array([math.cos(ph), math.sin(ph)]); vel[i] = math.sqrt(G / a) * np.array([-math.sin(ph), math.cos(ph)])
    v = v_inf * KMS
    pos[4] = np.array([-start, b_au]); vel[4] = np.array([v, 0.0])
    t = 0.0; T = start / v + years
    dmin = dict(sun=1e9, earth=1e9, nep=1e9)
    def acc(p):
        a = np.zeros_like(p)
        for i in range(5):
            d = p - p[i]; r3 = (np.sum(d * d, 1) + 1e-12) ** 1.5; r3[i] = np.inf
            a[i] = G * np.sum(m[:, None] * d / r3[:, None], 0)
        return a
    A = acc(pos)
    while t < T:
        rmin = min(np.linalg.norm(pos[4] - pos[j]) for j in range(4))
        dt = min(0.002 * max(rmin, 0.05) ** 1.5 / math.sqrt(M_BH), 0.002, 0.02)
        vel += 0.5 * dt * A; pos += dt * vel; A = acc(pos); vel += 0.5 * dt * A; t += dt
        dmin["sun"] = min(dmin["sun"], np.linalg.norm(pos[4] - pos[0]))
        dmin["earth"] = min(dmin["earth"], np.linalg.norm(pos[4] - pos[1]))
        dmin["nep"] = min(dmin["nep"], np.linalg.norm(pos[4] - pos[3]))
    out = {}
    for nm, i, M in (("earth", 1, 1.0), ("nep", 3, 1.0)):
        out[nm] = orbit_el(pos[i] - pos[0], vel[i] - vel[0], G * (1.0 + m[i]))
    return out, dmin


def theta_E_arcmin(d_au):
    return math.degrees(math.sqrt(2 * RS_KM / (d_au * AU_KM))) * 60


if __name__ == "__main__":
    print(f"Schwarzschild radius {RS_KM:.1f} km -> horizon {2 * RS_KM:.0f} km across")
    for d in (30, 10, 3, 2, 1, 0.5, 0.3):
        print(f"Einstein radius at {d:5.1f} AU: {theta_E_arcmin(d):.2f} arcmin")
    # pull on Neptune when the hole is 10 AU from it, vs the Sun's at 30 AU
    print("pull on Neptune at 10 AU vs Sun's:", round(M_BH / 10 ** 2 / (1 / 30.07 ** 2)))
    # tidal pull on Earth at 1 AU vs the Moon's tide
    print("tide at 1 AU vs Moon's:", round(M_BH * 333000 / 81.3 * 0 + (M_BH * 1.989e30 / 7.342e22) * (384400 / AU_KM) ** 3, 2))
    # Bondi accretion of solar wind at 1.5 AU from the Sun (n = 5 cm^-3 at 1 AU, falls as 1/r^2), v_rel ~ 450 km/s
    Gsi = 6.674e-11; M = M_BH * 1.989e30
    for r_au, eff in ((1.5, 1e-1), (1.5, 1e-3)):
        rho = 5e6 * 1.67e-27 / r_au ** 2; v = 4.5e5
        mdot = 4 * math.pi * Gsi ** 2 * M ** 2 * rho / v ** 3; L = eff * mdot * 2.998e8 ** 2
        mag = -26.74 - 2.5 * math.log10(L / 3.828e26 * (1.0 / 1.0) ** 2 / 1.0)   # seen from 1 AU away
        print(f"Bondi: r={r_au} AU mdot={mdot:.2e} kg/s, eff={eff}: L={L:.1e} W -> mag {mag:.1f} from 1 AU")
    # odds: n_BH ~ 1e-4 pc^-3 (1e8 holes in the Galaxy), v = 50 km/s, pass inside Neptune's orbit, with focusing
    pc_au = 206265.0; n = 1e-4 / pc_au ** 3; b = 30.07; v = 50 * KMS
    foc = 1 + 2 * G * (1 + M_BH) / (b * v * v)
    rate = n * math.pi * b * b * foc * v
    print(f"focusing x{foc:.2f}; one passage inside Neptune per {1 / rate:.2e} yr; chance in 10 Gyr {1e10 * rate:.1e}")
    for b in (2.5, 3.0, 3.5, 4.0, 5.0):
        for ph in (0.0, 1.5, 3.0, 4.5):
            el, dm = run(b, ph)
            a, e = el["earth"]
            print(f"b={b} phase={ph}: closest to Sun {dm['sun']:.2f} AU, to Earth {dm['earth']:.2f} AU, to Neptune {dm['nep']:.1f} AU"
                  f" -> Earth a={a:.2f} e={e:.2f}" + ("" if a == math.inf else f" (peri {a * (1 - e):.2f}, aph {a * (1 + e):.2f} AU)"))
