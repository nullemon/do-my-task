"""Locked timeline for "ONE TEASPOON OF A NEUTRON STAR" (seconds, 24 fps) + the numbers used on screen."""
import math
FPS = 24
DUR = 313.0
NFR = int(round(DUR * FPS))
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/11-neutron-star-teaspoon"

# voice line starts (measured Kokoro durations in audio/placement.json)
START = {'hook1': 0.8, 'hook2': 9.9, 'hook3': 18.2, 'form1': 27.0, 'form2': 40.2, 'size1': 58.0, 'size2': 69.9, 'dens1': 75.8,
         'dens2': 93.0, 'grav1': 110.0, 'grav2': 125.0, 'spin1': 137.4, 'spin2': 147.7, 'mag': 158.2, 'ans1': 170.0, 'ans2': 181.6,
         'thought1': 199.2, 'thought2': 210.1, 'thought3': 221.0, 'kilo1': 237.0, 'kilo2': 248.9, 'kilo3': 265.4, 'gold': 279.6,
         'end1': 288.6, 'end2': 299.4}

# shots: (name, start, end); neighbours cross-fade over XF seconds centred on the boundary
XF = 0.8
SHOTS = [("hook", 0.0, 21.6), ("title", 21.6, 26.8), ("giant", 26.8, 40.2), ("sn", 40.2, 57.8), ("city", 57.8, 74.8),
         ("dens", 74.8, 92.6), ("mass", 92.6, 109.4), ("grav", 109.4, 136.6), ("pulsar", 136.6, 157.6), ("magnetar", 157.6, 169.0),
         ("answer", 169.0, 198.2), ("thoughtA", 198.2, 220.4), ("thoughtB", 220.4, 236.4), ("merger", 236.4, 260.0),
         ("kilonova", 260.0, 279.4), ("gold", 279.4, 287.8), ("end", 287.8, 298.8), ("final", 298.8, DUR)]

# ------------------------------------------------------------------ physics used on screen (SI)
G = 6.674e-11; C = 2.998e8; MSUN = 1.989e30
M_NS = 1.4 * MSUN; R_NS = 12.0e3                      # a typical neutron star (NICER radii are ~12-13 km)
RS = 2 * G * M_NS / C ** 2                            # 4.13 km
RHO_MEAN = M_NS / (4 / 3 * math.pi * R_NS ** 3)       # 3.8e17 kg/m3
TSP = 5e-6                                            # one teaspoon, m3
G_SURF = G * M_NS / R_NS ** 2                         # 1.3e12 m/s2 (Newtonian)
V_ESC = C * math.sqrt(RS / R_NS)                      # 0.59 c
T_EARTH_FALL = math.pi / 2 * math.sqrt(6.371e6 / 9.81) / 60   # 21.1 min to the centre for a uniform Earth (PREM: ~19 min)

if __name__ == "__main__":
    print("rs km", RS / 1e3, "u", RS / R_NS, "mean density", RHO_MEAN, "teaspoon (t)", RHO_MEAN * TSP / 1e3)
    print("g surf", G_SURF, "x earth", G_SURF / 9.81, "1 m drop: t", math.sqrt(2 / G_SURF), "v km/s", math.sqrt(2 * G_SURF) / 1e3)
    print("v esc / c", V_ESC / C, "fall to centre (min)", T_EARTH_FALL)
    for m in (1e12, 2e12, 5e12):
        print("bead", m, "kg: 1 g at", math.sqrt(G * m / 9.81), "m; 1% mc2 =", 0.01 * m * C ** 2, "J; 1 MeV/nucleon =", m / 1.675e-27 * 1.602e-13, "J")
    print("visible fraction with bending", (1 - (1 - 1 / (1 - RS / R_NS))) / 2)
    print("rock swept on one pass (kg)", math.pi * 0.0106 ** 2 * 2 * 6.371e6 * 5510)
