"""Science numbers for "What If a Rogue Planet Passed Earth?" (every readout and on-screen size is computed here).
A Jupiter-mass, Jupiter-size rogue planet (no star). Constants: IAU / NASA fact sheets."""
import math

G = 6.674e-11
M_J, R_J = 1.89813e27, 69911.0          # kg, mean radius km
M_MOON, D_MOON, R_MOON = 7.342e22, 384400.0, 1737.4
M_SUN, AU = 1.98847e30, 1.495978707e8   # kg, km
R_E, M_E = 6371.0, 5.9722e24
F_PX = 1150.0                           # the city plate's lens (px): vertical FOV ~80 deg
ELEV = 34.0                             # the planet's elevation in the sky strip (deg)

DIST = {"nep": 50 * AU,                 # beyond Neptune (Neptune is at 30 AU)
        "mars": 55.76e6,                # as far as Mars at its closest (Aug 2003: 55.76 million km)
        "moon": D_MOON,                 # the Moon's distance
        "close": 200000.0}              # closest approach in the Short


def d_obs(a, elev=ELEV):
    e = math.radians(elev)
    return math.sqrt(a * a - (R_E * math.cos(e)) ** 2) - R_E * math.sin(e)


def ang_deg(a): return 2 * math.degrees(math.asin(R_J / d_obs(a)))
def rad_px(a): return F_PX * math.tan(math.asin(R_J / d_obs(a)))
def tide_vs_moon(a): return (M_J / M_MOON) * (D_MOON / a) ** 3
def pull_vs_sun(a): return (M_J / (a * 1e3) ** 2) / (M_SUN / (AU * 1e3) ** 2)


def roche_fluid_earth(): return 2.44 * R_J * (1.326 / 5.514) ** (1 / 3)


def kick(b_km, v_kms):
    """impulse-approximation velocity kick on Earth (km/s); only indicative when it comes out large"""
    return 2 * G * M_J / (b_km * 1e3 * v_kms * 1e3) / 1e3


def encounter_rate(b_km, n_pc3=0.025, v_kms=40.0):
    """passes within b of Earth per year: n * sigma * v, sigma = pi b^2 (with ~3x focusing by the Sun near 1 AU).
    n: Jupiter-mass rogues per pc^3 (<0.25 per star (Mroz et al. 2017) x ~0.1 stars per pc^3)"""
    pc = 3.0857e13
    sig = math.pi * (b_km / pc) ** 2
    v = v_kms / pc * 3.156e7
    return n_pc3 * sig * v * 3


if __name__ == "__main__":
    for k, a in DIST.items():
        th = ang_deg(a)
        print(f"{k:5s} d = {a:,.0f} km  -> {th:.4f} deg ({th * 3600:.1f} arcsec, {th / 0.518:.1f} Moon widths), r = {rad_px(a):.2f} px, "
              f"tide {tide_vs_moon(a):,.0f}x Moon, pull {pull_vs_sun(a):.3g}x Sun's")
    print(f"Earth inside its fluid Roche limit below {roche_fluid_earth():,.0f} km")
    th_e = math.sqrt(4 * G * M_J / (9e16 * D_MOON * 1e3)); alpha = 4 * G * M_J / (9e16 * R_J * 1e3)
    print(f"gravitational lensing at the Moon's distance: Einstein radius {math.degrees(th_e) * 3600:.0f}\", "
          f"deflection at the limb {math.degrees(alpha) * 3600:.3f}\" (negligible: the edge 'lensing' is atmospheric refraction)")
    print(f"kick at 200,000 km, 40 km/s: ~{kick(200000, 40):.0f} km/s (Earth's orbital speed 29.8, solar escape at 1 AU 42.1)")
    print(f"kick at the Moon's distance, 40 km/s: ~{kick(D_MOON, 40):.0f} km/s")
    print(f"passes within 200,000 km: ~1 per {1 / encounter_rate(200000):.1e} yr; within 1 AU ~1 per {1 / encounter_rate(AU):.1e} yr")
    print(f"brightness beyond Neptune: Jupiter-like albedo, r = Delta ~ 50 AU: m ~ {-2.94 + 5 * math.log10(50 * 49 / (5.2 * 4.2)):.1f}")
