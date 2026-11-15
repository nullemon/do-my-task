"""Science numbers for "What If Earth Had More Moons?" -- every on-screen size and readout is computed here.
Radii / masses / semi-major axes: NASA/JPL planetary & satellite fact sheets (mean radii, km; masses, kg).
Run it to print the table used in README.md."""
import math

GM_E = 3.986004e14          # m^3 s^-2
M_E, R_E = 5.9722e24, 6371.0
A_EARTH = 1.495978707e8     # km
M_SUN = 1.98847e30
M_MOON, R_MOON, D_MOON = 7.342e22, 1737.4, 384400.0
R_HILL = A_EARTH * (M_E / (3 * M_SUN)) ** (1 / 3)               # ~1.50 million km
F_PX = 10000.0              # telephoto lens of the Short (px); the frame is ~6.2 deg wide

# Jupiter's Galilean moons: radius, mass, semi-major axis (km)
GAL = {"io": (1821.6, 8.931938e22, 421700.0), "eur": (1560.8, 4.799844e22, 671034.0),
       "gan": (2634.1, 1.4819e23, 1070412.0), "cal": (2410.3, 1.075938e23, 1882709.0)}
# Saturn's moons: radius, mass, semi-major axis (km)
SAT = {"mim": (198.2, 3.7493e19, 185539.0), "enc": (252.1, 1.08022e20, 237948.0), "tet": (531.1, 6.17449e20, 294619.0),
       "dio": (561.4, 1.095452e21, 377396.0), "rhe": (763.8, 2.306518e21, 527108.0), "tit": (2574.7, 1.345452e23, 1221870.0),
       "hyp": (135.0, 5.6199e18, 1481009.0), "jan": (89.5, 1.8975e18, 151460.0), "epi": (58.1, 5.266e17, 151410.0),
       "pro": (43.1, 1.5956e17, 139380.0), "pan": (40.6, 1.3709e17, 141720.0)}
PHOBOS_R, PHOBOS_A, PHOBOS_AXES = 11.08, 20000.0, (27.0, 22.0, 18.0)     # Phobos-like moon at 20,000 km
DEIMOS_R, DEIMOS_A = 6.2, 44000.0                                     # Deimos-like at 44,000 km (just past GEO)
K_JUP = D_MOON / GAL["gan"][2]          # Jupiter-style system scaled so Ganymede sits at the Moon's distance
K_SAT = D_MOON / SAT["tit"][2]          # Saturn-style system scaled so Titan sits at the Moon's distance
A_TWO = D_MOON * 2 ** (2 / 3)           # second Moon in a 2:1 resonance with ours (1.587x the distance)


def d_obs(a, elev_deg=2.0):
    """observer-to-moon distance (km) for a moon at geocentric distance a seen at elevation elev (the Short looks at the
    low sky over the lake, 0-8 deg up)"""
    e = math.radians(elev_deg)
    return math.sqrt(a * a - (R_E * math.cos(e)) ** 2) - R_E * math.sin(e)


def ang_deg(R, a, elev=2.0): return 2 * math.degrees(math.asin(R / d_obs(a, elev)))
def rad_px(R, a, elev=2.0): return F_PX * math.tan(math.asin(R / d_obs(a, elev)))
def period_h(a_km): return 2 * math.pi * math.sqrt((a_km * 1e3) ** 3 / GM_E) / 3600
def tide(M, a): return (M / M_MOON) * (D_MOON / a) ** 3       # tidal acceleration relative to our Moon's


def roche_fluid(rho):   # km, density g/cc
    return 2.44 * R_E * (5.514 / rho) ** (1 / 3)


def mutual_hill(m1, a1, m2, a2):
    """separation of two orbits in mutual Hill radii"""
    rh = (a1 + a2) / 2 * ((m1 + m2) / (3 * M_E)) ** (1 / 3)
    return abs(a2 - a1) / rh


if __name__ == "__main__":
    print(f"Earth Hill radius {R_HILL:,.0f} km; prograde stability ~0.49 r_H = {0.49 * R_HILL:,.0f} km")
    print(f"Moon: {ang_deg(R_MOON, D_MOON):.3f} deg, r = {rad_px(R_MOON, D_MOON):.1f} px, period {period_h(D_MOON) / 24:.2f} d")
    print(f"Second Moon (2:1): a = {A_TWO:,.0f} km = {A_TWO / D_MOON:.3f} x, {A_TWO / R_HILL:.2f} r_H, {ang_deg(R_MOON, A_TWO):.3f} deg, "
          f"r = {rad_px(R_MOON, A_TWO):.1f} px, period {period_h(A_TWO) / 24:.1f} d (ours {period_h(D_MOON) / 24:.1f} d), "
          f"mutual Hill sep {mutual_hill(M_MOON, D_MOON, M_MOON, A_TWO):.2f}")
    print(f"Phobos-like a = {PHOBOS_A:,.0f} km: period {period_h(PHOBOS_A):.2f} h (Phobos 7.65 h); synodic "
          f"{1 / (1 / period_h(PHOBOS_A) - 1 / 23.934):.1f} h; at 2 deg elev d = {d_obs(PHOBOS_A):,.0f} km, "
          f"{ang_deg(PHOBOS_R, PHOBOS_A):.4f} deg mean ({ang_deg(PHOBOS_R, PHOBOS_A) * 60:.1f}'), r = {rad_px(PHOBOS_R, PHOBOS_A):.2f} px; "
          f"overhead {2 * math.degrees(PHOBOS_R / (PHOBOS_A - R_E)):.3f} deg")
    print(f"  fluid Roche limit for Phobos density 1.86: {roche_fluid(1.86):,.0f} km (rigid ~{roche_fluid(1.86) / 2.44 * 1.26:,.0f})")
    print(f"Deimos-like a = {DEIMOS_A:,.0f} km: period {period_h(DEIMOS_A):.1f} h; {ang_deg(DEIMOS_R, DEIMOS_A) * 60:.2f}' , r = "
          f"{rad_px(DEIMOS_R, DEIMOS_A):.2f} px")
    print(f"Jupiter-style, scale {K_JUP:.4f} (Ganymede at the Moon's distance):")
    for k, (R, M, a) in GAL.items():
        A = a * K_JUP
        print(f"  {k}: a = {A:,.0f} km ({A / R_HILL:.2f} r_H), {ang_deg(R, A):.3f} deg ({R / R_MOON * D_MOON / A * 1:.2f}x Moon's width),"
              f" r = {rad_px(R, A):.1f} px, tide {tide(M, A):.1f}x Moon, period {period_h(A) / 24:.2f} d")
    ks = list(GAL)
    for i in range(3):
        a1, a2 = GAL[ks[i]], GAL[ks[i + 1]]
        print(f"  mutual Hill {ks[i]}-{ks[i + 1]}: {mutual_hill(a1[1], a1[2] * K_JUP, a2[1], a2[2] * K_JUP):.2f}")
    io = GAL["io"]; gan = GAL["gan"]
    k = (gan[2] - io[2]) * K_JUP; sun = math.radians(0.2666)
    print(f"  Io shadow on Ganymede: {k:,.0f} km behind Io: umbra {2 * (io[0] - k * math.tan(sun)):,.0f} km, penumbra "
          f"{2 * (io[0] + k * math.tan(sun)):,.0f} km (Ganymede {2 * gan[0]:,.0f} km)")
    print(f"Saturn-style, scale {K_SAT:.4f} (Titan at the Moon's distance):")
    for k, (R, M, a) in SAT.items():
        A = a * K_SAT
        print(f"  {k}: a = {A:,.0f} km, {ang_deg(R, A):.3f} deg, r = {rad_px(R, A):.1f} px, tide {tide(M, A):.3f}x")
    print(f"  fluid Roche limit, ice (0.95 g/cc): {roche_fluid(0.95):,.0f} km; rock (3.3): {roche_fluid(3.3):,.0f} km")
